"""
Assumptions:

Steps / Key Functions:
1. Augment Data 
2. Create Patches
3. Embed Patches
4. Create MLP 
5. Create Transformer Encoder
5. Create ViT

References:
1) https://keras.io/examples/vision/image_classification_with_vision_transformer/
2) https://towardsdatascience.com/understand-and-implement-vision-transformer-with-tensorflow-2-0-f5435769093

"""

##############################  INPUT DATA AUGMENTATION  ###################################

def data_augmentation(mean, variance):
    """ data augmentation for input data based on calculated mean and variance of training data """

    data_augmentation = keras.Sequential(
        [
            layers.Normalization(mean=mean, variance=variance),
        ],
        name="data_augmentation",
    )

    return data_augmentation


###################################  CREATE PATCHES  #######################################

class Patches(layers.Layer):
    """ Class to create patches from input images"""
    def __init__(self, patch_size):
        """ Constructor calling Layers first"""
        super(Patches, self).__init__()
        self.patch_size = patch_size

    def call(self, images):
        """ Allows Patches class to act like a method with images as input """
        batch_size = tf.shape(images)[0]
        patches = tf.image.extract_patches(
            images=images,
            sizes=[1, self.patch_size, self.patch_size, 1],
            strides=[1, self.patch_size, self.patch_size, 1],
            rates=[1, 1, 1, 1],
            padding="SAME",
        )
        patch_dims = patches.shape[-1]
        patches = tf.reshape(patches, [batch_size, -1, patch_dims])
        return patches

###################################  EMBED PATCHES  #######################################

class PatchEmbedding(layers.Layer):
    """ Class to linear project flattened patch into projection_dim and add positional embedding"""
    def __init__(self, num_patches, projection_dim):
        super(PatchEmbedding, self).__init__()
        self.num_patches = num_patches
        self.projection = layers.Dense(units=projection_dim)
        self.position_embedding = layers.Embedding(
            input_dim=num_patches, output_dim=projection_dim
        )

    def call(self, patch):
        positions = tf.range(start=0, limit=self.num_patches, delta=1)
        
        # add linear project to position embedding
        embedding = self.projection(patch) + self.position_embedding(positions)
        return embedding

###################################  CREATE MLP  #######################################

def mlp(x, hidden_units, dropout_rate):
    """ Generic function to create zero or more mlp blocks each a dense layer and a dropout layer  """
    
    for units in hidden_units:
        x = layers.Dense(units, activation=tf.keras.activations.tanh)(x)
        x = layers.Dropout(dropout_rate)(x)
    return x