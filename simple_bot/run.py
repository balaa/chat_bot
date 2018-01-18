from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging

import sys
import warnings

from rasa_core import utils
from rasa_core.actions import Action
from rasa_core.agent import Agent
from rasa_core.channels.console import ConsoleInputChannel
from rasa_core.interpreter import RasaNLUInterpreter
from rasa_core.policies.keras_policy import KerasPolicy
from rasa_core.policies.memoization import MemoizationPolicy

logger = logging.getLogger(__name__)


class RestaurantPolicy(KerasPolicy):
    def model_architecture(self, num_features, num_actions, max_history_len):
        """Build a Keras model and return a compiled model."""
        from keras.layers import LSTM, Activation, Masking, Dense
        from keras.models import Sequential

        n_hidden = 32  # size of hidden layer in LSTM
        # Build Model
        batch_shape = (None, max_history_len, num_features)

        model = Sequential()
        model.add(Masking(-1, batch_input_shape=batch_shape))
        model.add(LSTM(n_hidden, batch_input_shape=batch_shape))
        model.add(Dense(input_dim=n_hidden, output_dim=num_actions))
        model.add(Activation('softmax'))

        model.compile(loss='categorical_crossentropy',
                      optimizer='adam',
                      metrics=['accuracy'])

        logger.debug(model.summary())
        return model


def train_dialogue(domain_file="ecapp_domain.yml",
                   model_path="models/dialogue",
                   training_data_file="data/stories.md"):
    agent = Agent(domain_file,
                  policies=[MemoizationPolicy(), RestaurantPolicy()])

    agent.train(
            training_data_file,
            max_history=3,
            epochs=900,
            batch_size=50,
            augmentation_factor=50,
            validation_split=0.2
    )

    agent.persist(model_path)
    return agent


def train_nlu():
    from rasa_nlu.converters import load_data
    from rasa_nlu.config import RasaNLUConfig
    from rasa_nlu.model import Trainer

    training_data = load_data('data/nlu.json')
    trainer = Trainer(RasaNLUConfig("nlu_model_config.json"))
    trainer.train(training_data)
    model_directory = trainer.persist('models/nlu/', fixed_model_name="current")

    return model_directory


def run(serve_forever=True):
    interpreter = RasaNLUInterpreter("models/nlu/current")
    agent = Agent.load("models/dialogue", interpreter=interpreter)

    if serve_forever:
        agent.handle_channel(ConsoleInputChannel())
    return agent


if __name__ == '__main__':
    utils.configure_colored_logging("DEBUG")

    parser = argparse.ArgumentParser(
            description='starts the bot')

    parser.add_argument(
            'task',
            choices=["train-nlu", "train-dialogue", "run"],
            help="what the bot should do - e.g. run or train?")
    task = parser.parse_args().task

    # decide what to do based on first parameter of the script
    if task == "train-nlu":
        train_nlu()
    elif task == "train-dialogue":
        train_dialogue()
    elif task == "run":
        run()
    else:
        warnings.warn("Need to pass either 'train-nlu', 'train-dialogue' or "
                      "'run' to use the script.")
        exit(1)
