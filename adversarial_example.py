import matplotlib as mpl
# This line allows mpl to run with no DISPLAY defined
mpl.use('Agg')

from keras.layers import Dense, Reshape, Flatten
from keras.models import Sequential
from keras.optimizers import Adam
from keras.regularizers import l1
from keras.datasets import mnist
import pandas as pd
import numpy as np


from adversarial import AdversarialModel, GenerateSamplesCallback, simple_gan, gan_targets
from adversarial import AdversarialOptimizerSimultaneous, normal_latent_sampling


def model_generator(latent_dim, input_shape, hidden_dim=512, activation="tanh", reg=lambda: l1(1e-7)):
    return Sequential([
        Dense(hidden_dim, name="generator_h1", input_dim=latent_dim, activation=activation, W_regularizer=reg()),
        Dense(hidden_dim, name="generator_h2", input_dim=latent_dim, activation=activation, W_regularizer=reg()),
        Dense(np.prod(input_shape), name="generator_x_flat", activation="sigmoid", W_regularizer=reg()),
        Reshape(input_shape, name="generator_x")],
        name="generator")


def model_discriminator(input_shape, output_dim=1, hidden_dim=256, activation="tanh", reg=lambda: l1(1e-3)):
    return Sequential([
        Flatten(name="discriminator_flatten", input_shape=input_shape),
        Dense(hidden_dim, name="discriminator_h1", input_dim=latent_dim, activation=activation, W_regularizer=reg()),
        Dense(hidden_dim, name="discriminator_h2", input_dim=latent_dim, activation=activation, W_regularizer=reg()),
        Dense(output_dim, name="discriminator_y", activation="sigmoid", W_regularizer=reg())],
        name="discriminator")


def mnist_process(x):
    x = x.astype(np.float32) / 255.0
    return x


def mnist_data():
    (xtrain, ytrain), (xtest, ytest) = mnist.load_data()
    return mnist_process(xtrain), mnist_process(xtest)


if __name__ == "__main__":
    # z \in R^100
    latent_dim = 100
    # x \in R^{28x28}
    input_shape = (28, 28)

    # generator (z -> x)
    generator = model_generator(latent_dim, input_shape)
    # discriminator (x -> y)
    discriminator = model_discriminator(input_shape)
    # gan (x - > yfake, yreal), z generated on GPU
    gan = simple_gan(generator, discriminator, normal_latent_sampling((latent_dim,)))

    # print summary of models
    generator.summary()
    discriminator.summary()
    gan.summary()

    # build adversarial model
    model = AdversarialModel(base_model=gan,
                             player_params=[generator.trainable_weights, discriminator.trainable_weights],
                             player_names=["generator", "discriminator"])
    model.adversarial_compile(adversarial_optimizer=AdversarialOptimizerSimultaneous(),
                              player_optimizers=[Adam(1e-4, decay=1e-4), Adam(1e-3, decay=1e-4)],
                              loss='binary_crossentropy')

    # train model
    zsamples = np.random.normal(size=(10 * 10, latent_dim))
    cb = GenerateSamplesCallback("output/gan/epoch-{}.png",
                                 lambda: generator.predict(zsamples).reshape((10, 10, 28, 28)))
    xtrain, xtest = mnist_data()
    y = gan_targets(xtrain.shape[0])
    ytest = gan_targets(xtest.shape[0])
    history = model.fit(x=xtrain, y=y, validation_data=(xtest, ytest), callbacks=[cb], nb_epoch=50, batch_size=32)
    df = pd.DataFrame(history.history)
    df.to_csv("output/gan/history.csv")
