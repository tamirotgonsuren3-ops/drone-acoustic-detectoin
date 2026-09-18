package com.soundsense.drone.ml

import android.content.Context
import android.util.Log
import java.io.DataInputStream
import java.io.FileInputStream
import kotlin.math.abs
import kotlin.math.log10
import kotlin.math.sqrt

class AudioClassifier(private val context: Context) {

    companion object {
        private const val TAG = "AudioClassifier"
        private const val N_MFCC = 20
        private const val N_FFT = 2048
        private const val HOP_LENGTH = 512
    }

    data class ClassificationResult(
        val label: String,
        val confidence: Double,
        val allScores: Map<String, Double> = emptyMap()
    )

    private var isModelLoaded = false
    private var modelWeights: Array<Array<FloatArray>>? = null
    private var modelBiases: Array<FloatArray>? = null
    private var labels: List<String> = emptyList()
    private var inputSize: Int = 0

    init {
        loadModel()
    }

    private fun loadModel() {
        try {
            val files = context.filesDir.listFiles() ?: return
            val modelFile = files.find { it.name == "model.bin" }
            val labelsFile = files.find { it.name == "labels.txt" }

            if (modelFile != null && labelsFile != null) {
                loadModelBinary(modelFile.absolutePath)
                labels = labelsFile.readLines().filter { it.isNotBlank() }
                isModelLoaded = true
                Log.d(TAG, "Model loaded: ${labels.size} classes, input=$inputSize")
            } else {
                Log.w(TAG, "No trained model found, using built-in rules")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Model load error", e)
        }
    }

    private fun loadModelBinary(path: String) {
        val dis = DataInputStream(FileInputStream(path))
        val nLayers = dis.readInt()
        val layerSizes = IntArray(nLayers) { dis.readInt() }
        inputSize = layerSizes.firstOrNull() ?: 0

        modelWeights = Array(nLayers - 1) { i ->
            val rows = layerSizes[i]
            val cols = layerSizes[i + 1]
            Array(rows) { readFloatArray(dis, cols) }
        }

        modelBiases = Array(nLayers - 1) { i ->
            readFloatArray(dis, layerSizes[i + 1])
        }
        dis.close()
    }

    private fun readFloatArray(dis: DataInputStream, size: Int): FloatArray {
        return FloatArray(size) { dis.readFloat() }
    }

    fun classify(samples: FloatArray, sampleRate: Int): ClassificationResult? {
        val features = extractFeatures(samples, sampleRate)

        if (isModelLoaded && modelWeights != null) {
            return classifyWithModel(features)
        }

        return classifyWithRules(samples, sampleRate)
    }

    private fun classifyWithModel(features: FloatArray): ClassificationResult {
        var current = features.copyOf()

        for (layer in modelWeights!!.indices) {
            val weights = modelWeights!![layer]
            val biases = modelBiases!![layer]
            val output = FloatArray(biases.size)

            for (j in output.indices) {
                var sum = biases[j]
                for (i in current.indices) {
                    sum += current[i] * weights[i][j]
                }
                output[j] = if (layer < modelWeights!!.size - 1) {
                    maxOf(0f, sum)
                } else {
                    sum
                }
            }
            current = output
        }

        val expValues = current.map { Math.exp(it.toDouble()).toFloat() }
        val expSum = expValues.sum()
        val probs = expValues.map { it / expSum }

        val maxIdx = probs.indices.maxByOrNull { probs[it] } ?: 0
        val confidence = probs[maxIdx].toDouble()

        val allScores = if (labels.size == probs.size) {
            labels.zip(probs.map { p -> p.toDouble() }).toMap()
        } else {
            probs.mapIndexed { idx, p -> "class_$idx" to p.toDouble() }.toMap()
        }

        val label = if (maxIdx < labels.size) labels[maxIdx] else "unknown_$maxIdx"
        return ClassificationResult(label, confidence, allScores)
    }

    private fun classifyWithRules(samples: FloatArray, sampleRate: Int): ClassificationResult {
        val rms = sqrt(samples.map { it * it }.average()).toFloat()
        val zeroCrossing = countZeroCrossings(samples)
        val zcr = zeroCrossing.toFloat() / samples.size

        val spectrum = computeSpectrum(samples)
        val lowEnergy = spectrum.take(spectrum.size / 4).map { it.toDouble() }.average()
        val midEnergy = spectrum.drop(spectrum.size / 4).take(spectrum.size / 2).map { it.toDouble() }.average()
        val highEnergy = spectrum.drop(3 * spectrum.size / 4).map { it.toDouble() }.average()

        val bassRatio = lowEnergy / (midEnergy + 0.001)
        val trebleRatio = highEnergy / (midEnergy + 0.001)

        return when {
            rms > 0.15f && bassRatio > 2.0 -> ClassificationResult("loud_sound", minOf(0.9, 0.5 + rms))
            zcr > 0.15f && trebleRatio > 1.5 -> ClassificationResult("high_pitch_sound", minOf(0.85, 0.4 + trebleRatio * 0.15))
            rms > 0.08f && bassRatio > 1.2 -> ClassificationResult("drone", minOf(0.8, 0.45 + bassRatio * 0.1))
            rms > 0.05f -> ClassificationResult("ambient_noise", minOf(0.7, 0.3 + rms * 2))
            else -> ClassificationResult("silence", 0.6)
        }
    }

    private fun extractFeatures(samples: FloatArray, sampleRate: Int): FloatArray {
        val mfcc = computeMFCC(samples, sampleRate)
        val chroma = computeChroma(samples, sampleRate)
        val mel = computeMel(samples, sampleRate)

        return mfcc + chroma + mel
    }

    private fun computeMFCC(samples: FloatArray, sampleRate: Int): FloatArray {
        val spectrum = computeSpectrum(samples)
        val melFilters = createMelFilterBank(N_FFT / 2 + 1, 40, sampleRate)
        val melEnergies = FloatArray(40) { i ->
            val sum = melFilters[i].zip(spectrum).map { (f, s) -> f * s }.sum()
            sum.coerceAtLeast(1e-10f)
        }
        return FloatArray(N_MFCC) { k ->
            var sum = 0.0
            for (i in 0 until 40) {
                sum += melEnergies[i] * Math.cos(Math.PI * k * (2 * i + 1.0) / (2.0 * 40))
            }
            sum.toFloat()
        }
    }

    private fun computeChroma(samples: FloatArray, sampleRate: Int): FloatArray {
        val spectrum = computeSpectrum(samples)
        val chroma = FloatArray(12)
        val freqPerBin = sampleRate.toFloat() / N_FFT

        for (i in spectrum.indices) {
            val freq = i * freqPerBin
            if (freq > 0) {
                val midi = 69 + 12 * log10(freq / 440.0) / log10(2.0)
                val bin = (midi % 12).toInt().coerceIn(0, 11)
                chroma[bin] += spectrum[i]
            }
        }
        val maxChroma = chroma.maxOrNull() ?: 1f
        return chroma.map { c -> c / maxChroma }.toFloatArray()
    }

    private fun computeMel(samples: FloatArray, sampleRate: Int): FloatArray {
        val spectrum = computeSpectrum(samples)
        val melFilters = createMelFilterBank(N_FFT / 2 + 1, 20, sampleRate)
        val melEnergies = FloatArray(20) { i ->
            val sum = melFilters[i].zip(spectrum).map { (f, s) -> f * s }.sum()
            sum.coerceAtLeast(1e-10f)
        }
        return melEnergies.map { e -> log10(e) }.toFloatArray()
    }

    private fun computeSpectrum(samples: FloatArray): FloatArray {
        val n = minOf(samples.size, N_FFT)
        val padded = FloatArray(N_FFT)
        System.arraycopy(samples, 0, padded, 0, n)

        for (i in 0 until n / 2) {
            val window = (0.54 - 0.46 * Math.cos(2.0 * Math.PI * i / (n - 1))).toFloat()
            padded[i] *= window
        }

        val spectrum = FloatArray(N_FFT / 2)

        for (k in 0 until N_FFT / 2) {
            var re = 0f
            var im = 0f
            val limit = minOf(N_FFT, samples.size)
            for (j in 0 until limit) {
                val angle = 2.0 * Math.PI * k * j / N_FFT
                re += padded[j] * Math.cos(angle).toFloat()
                im -= padded[j] * Math.sin(angle).toFloat()
            }
            spectrum[k] = sqrt(re * re + im * im) / N_FFT
        }

        return spectrum
    }

    private fun createMelFilterBank(size: Int, nFilters: Int, sampleRate: Int): Array<FloatArray> {
        val lowMel = 0f
        val highMel = (2595 * log10(1 + (sampleRate / 2f) / 700f)).toFloat()
        val melPoints = FloatArray(nFilters + 2) { i ->
            lowMel + i * (highMel - lowMel) / (nFilters + 1)
        }
        val bins = melPoints.map { mel ->
            ((size - 1) * (700 * (Math.pow(10.0, mel / 2595.0) - 1)) / (sampleRate / 2)).toInt().coerceIn(0, size - 1)
        }

        return Array(nFilters) { i ->
            FloatArray(size) { j ->
                when {
                    j in bins[i]..bins[i + 1] && bins[i] != bins[i + 1] ->
                        (j - bins[i]).toFloat() / (bins[i + 1] - bins[i])
                    j in bins[i + 1]..bins[i + 2] && bins[i + 1] != bins[i + 2] ->
                        (bins[i + 2] - j).toFloat() / (bins[i + 2] - bins[i + 1])
                    else -> 0f
                }
            }
        }
    }

    private fun countZeroCrossings(samples: FloatArray): Int {
        var count = 0
        for (i in 1 until samples.size) {
            if ((samples[i] >= 0) != (samples[i - 1] >= 0)) count++
        }
        return count
    }
}
