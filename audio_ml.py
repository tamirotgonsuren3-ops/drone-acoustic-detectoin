import os
import json
import uuid
import numpy as np
import librosa
import soundfile as sf
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import pickle


class AudioMLTrainer:
    def __init__(self, model_folder='models'):
        self.model_folder = model_folder
        self.model = None
        self.label_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.classes = []
        os.makedirs(model_folder, exist_ok=True)

    def extract_features(self, file_path, sr=22050, n_mfcc=20):
        try:
            y, sr = librosa.load(file_path, sr=sr, duration=5.0)
            if len(y) < sr:
                y = np.pad(y, (0, sr - len(y)))
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            mel = librosa.feature.melspectrogram(y=y, sr=sr)
            mel_mean = np.mean(mel, axis=1)
            features = np.concatenate([mfcc_mean, mfcc_std, chroma_mean, mel_mean])
            return features
        except Exception as e:
            print(f"[ML] Feature extraction error for {file_path}: {e}")
            return None

    def prepare_dataset(self, upload_folder):
        X = []
        y = []
        file_map = {}

        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            if not os.path.isfile(filepath):
                continue

            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext not in ('mp3', 'mp4', 'wav', 'ogg', 'flac', 'm4a'):
                continue

            parts = filename.split('_', 1)
            if len(parts) < 2:
                parts = filename.split('-', 1)

            sound_type = None
            for key in file_map:
                if key in filename:
                    sound_type = file_map[key]
                    break

            if sound_type is None:
                continue

            features = self.extract_features(filepath)
            if features is not None:
                X.append(features)
                y.append(sound_type)

        return np.array(X), np.array(y)

    def train(self, upload_folder, epochs=50):
        try:
            files = os.listdir(upload_folder)
            if not files:
                return {'success': False, 'error': 'No files found'}

            sound_types = set()
            file_map = {}
            for f in files:
                parts = f.split('_', 1)
                if len(parts) < 2:
                    parts = f.split('-', 1)
                if len(parts) >= 2:
                    remainder = parts[1]
                    for ext in ('.mp3', '.mp4', '.wav', '.ogg', '.flac', '.m4a'):
                        remainder = remainder.replace(ext, '')
                    if remainder:
                        sound_types.add(remainder)
                        file_map[f] = remainder

            if not sound_types:
                return {'success': False, 'error': 'Could not determine sound types from filenames. Use format: type_filename.ext'}

            for f in files:
                for st in sound_types:
                    if st in f and f not in file_map:
                        file_map[f] = st

            print(f"[ML] Found sound types: {sound_types}")
            print(f"[ML] File mapping: {file_map}")

            X = []
            y = []
            for filename, sound_type in file_map.items():
                filepath = os.path.join(upload_folder, filename)
                if not os.path.isfile(filepath):
                    continue
                features = self.extract_features(filepath)
                if features is not None:
                    X.append(features)
                    y.append(sound_type)
                    print(f"[ML] Extracted features from {filename} -> {sound_type}")

            if len(X) < 2:
                return {'success': False, 'error': f'Need at least 2 samples, found {len(X)}'}

            X = np.array(X)
            y = np.array(y)

            self.classes = list(set(y))
            y_encoded = self.label_encoder.fit_transform(y)
            X_scaled = self.scaler.fit_transform(X)

            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
            )

            self.model = MLPClassifier(
                hidden_layer_sizes=(128, 64, 32),
                activation='relu',
                max_iter=epochs,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.15
            )
            self.model.fit(X_train, y_train)

            train_acc = self.model.score(X_train, y_train)
            test_acc = self.model.score(X_test, y_test) if len(X_test) > 0 else train_acc

            print(f"[ML] Training accuracy: {train_acc:.2%}")
            print(f"[ML] Test accuracy: {test_acc:.2%}")

            model_path = os.path.join(self.model_folder, 'model.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'label_encoder': self.label_encoder,
                    'scaler': self.scaler,
                    'classes': self.classes,
                    'n_features': X.shape[1]
                }, f)

            meta_path = os.path.join(self.model_folder, 'model_meta.json')
            with open(meta_path, 'w') as f:
                json.dump({
                    'classes': self.classes,
                    'accuracy': float(test_acc),
                    'n_samples': len(X),
                    'n_features': int(X.shape[1])
                }, f)

            export_info = self._export_to_tfjs()

            return {
                'success': True,
                'classes': self.classes,
                'accuracy': float(test_acc),
                'train_accuracy': float(train_acc),
                'n_samples': len(X),
                'model_path': model_path,
                'tfjs_export': export_info
            }

        except Exception as e:
            print(f"[ML] Training error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def _export_to_tfjs(self):
        try:
            try:
                import tensorflow as tf
                from tensorflow import keras

                n_features = self.model.coefs_[0].shape[0]
                n_classes = len(self.classes)

                model = keras.Sequential()
                model.add(keras.layers.InputLayer(input_shape=(n_features,)))

                for i, layer_size in enumerate(self.model.hidden_layer_sizes):
                    weights = self.model.coefs_[i]
                    bias = self.model.intercepts_[i].reshape(-1)
                    model.add(keras.layers.Dense(layer_size, activation='relu',
                                                  weights=[weights, bias]))

                output_weights = self.model.coefs_[-1]
                output_bias = self.model.intercepts_[-1].reshape(-1)
                model.add(keras.layers.Dense(n_classes, activation='softmax',
                                              weights=[output_weights, output_bias]))

                tfjs_model_path = os.path.join(self.model_folder, 'model')
                try:
                    import tensorflowjs as tfjs
                    tfjs.converters.save_keras_model(model, tfjs_model_path)
                    print(f"[ML] Exported TensorFlow.js model to {tfjs_model_path}")
                    return {'tfjs': True, 'path': tfjs_model_path}
                except ImportError:
                    keras_model_path = os.path.join(self.model_folder, 'model.h5')
                    model.save(keras_model_path)
                    print(f"[ML] Saved Keras model (install tensorflowjs for TF.js export)")
                    return {'keras': True, 'path': keras_model_path}

            except ImportError:
                print("[ML] TensorFlow not available, using Python-only model")
                return {'python_only': True}

        except Exception as e:
            print(f"[ML] Export error: {e}")
            return {'error': str(e)}

    def predict(self, file_path):
        model_path = os.path.join(self.model_folder, 'model.pkl')
        if not os.path.exists(model_path):
            return {'error': 'No trained model found'}

        with open(model_path, 'rb') as f:
            data = pickle.load(f)

        model = data['model']
        le = data['label_encoder']
        scaler = data['scaler']

        features = self.extract_features(file_path)
        if features is None:
            return {'error': 'Could not extract features'}

        features_scaled = scaler.transform(features.reshape(1, -1))
        probabilities = model.predict_proba(features_scaled)[0]
        predicted_idx = np.argmax(probabilities)
        predicted_class = le.inverse_transform([predicted_idx])[0]
        confidence = float(probabilities[predicted_idx])

        all_probs = {}
        for i, cls in enumerate(le.classes_):
            all_probs[cls] = float(probabilities[i])

        return {
            'prediction': predicted_class,
            'confidence': confidence,
            'probabilities': all_probs
        }
