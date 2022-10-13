"""
Contains source code of components of alzheimers classification model.
"""
import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras import layers
import numpy as np

from dataset import IMAGE_DIM, make_patch

class AlzheimerModel(keras.Model):
    def __init__(self, num_patches, num_layers, num_heads, d_model, d_mlp, head_layers, dropout_rate, num_classes):
        """Initialise the model"""
        super().__init__()

        #Data augmentation
        self.augmentation = keras.Sequential([
            layers.Rescaling(1 / 255.0),
            layers.RandomRotation(0.2),
            layers.RandomFlip()
        ])

        #Apply projection and positional encoding
        self.pos_encoder = PositionalEncoder(num_patches, d_model)

        #Nx Transformer Encoders
        self.encoders = [TransformerEncoder(num_heads, d_model, d_mlp, dropout_rate) for _ in range(num_layers)]

        #MLP Head
        self.mlp = MultiLayerPerceptron(head_layers, d_model, dropout_rate)

        #OUTPUT
        self.classification = layers.Dense(num_classes, activation="softmax")
    
    def call(self, x):
        """Use the model with .fit"""
        x = self.augmentation(x)

        x = make_patch(x)

        x = self.pos_encoder(x)

        for encoder in self.encoders:
            x = encoder(x)
        
        head_mlp = self.mlp(x[:, 0, :])
        
        output = self.classification(head_mlp)

        return output

class PositionalEncoder(layers.Layer):
    def __init__(self, num_patches, d_model) -> None:
        super().__init__()
        self.num_patches = num_patches
        self.d_model = d_model

        self.projection = layers.Dense(d_model)
        self.cls_token = self.add_weight("cls_token", shape=(1, 1, d_model))
        self.pos_embedding = layers.Embedding(num_patches+1, d_model)
    
    def call(self, x):
        positions = tf.tile([tf.range(0, self.num_patches+1)], [tf.shape(x)[0], 1])
        pos_emb = self.pos_embedding(positions)

        linear_map = self.projection(x)
        cls_token = tf.tile(self.cls_token, [tf.shape(x)[0], 1, 1]) #[BATCH_SIZE, 1, self.d_model]
        class_embedded = tf.concat([cls_token, linear_map], 1)
        encoded = class_embedded + pos_emb
        return encoded

class TransformerEncoder(layers.Layer):
    def __init__(self, heads, d_model, d_mlp, dropout_rate=0.1):
        """
        Initialise the encoder layer
        heads: Number of heads for self-attention blocks
        d_model: Dimensionality of the image patches
        d_mlp: Dimensionality of the MLP block
        """
        super().__init__()

        self.self_attention = SelfAttention(heads, d_model, dropout_rate)
        self.multi_layer_perceptron = MultiLayerPerceptron(d_mlp, d_model, dropout_rate)

    def call(self, x):
        """Apply the transformer encoder on data inputs"""
        self_attention = self.self_attention(x)
        result = self.multi_layer_perceptron(self_attention)
        return result
        
class SelfAttention(layers.Layer):
    def __init__(self, heads, d_model, dropout_rate):
        """Initialise the self attention layer"""
        super().__init__()

        self.layer_normalisation = layers.LayerNormalization()
        self.mha = layers.MultiHeadAttention(num_heads=heads, key_dim=d_model, dropout=dropout_rate)
        self.add = layers.Add()

    def call(self, x):
        """Apply self attention on data inputs"""
        x_norm = self.layer_normalisation(x)
        self_attention = self.mha(query=x_norm, value=x_norm, key=x_norm)

        result = self.add([x, self_attention])

        return result

class MultiLayerPerceptron(layers.Layer):
    def __init__(self, d_mlp, d_model, dropout_rate):
        """Initialise the multi layer perceptron"""
        super().__init__()

        self.layer_normalisation = layers.LayerNormalization()
        self.mlp = keras.Sequential([
            layers.Dense(d_mlp, activation="gelu"),
            layers.Dense(d_model),
            layers.Dropout(dropout_rate)
        ])
        self.add = layers.Add()

    def call(self, x):
        """Apply MLP to data inputs"""
        x_norm = self.layer_normalisation(x)
        mlp = self.mlp(x_norm)
        result = self.add([x, mlp])

        return result