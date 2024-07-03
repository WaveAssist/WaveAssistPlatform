##PYTHON IMPORTS
import os
from Utils.Logger import Logger
##Logger
logger = Logger()


##ToDo: Check if this function handles all cases.
def generate_flow_layers(dependencies_dict):
    try:
        layers = []
        initial_layer = [key for key, value in dependencies_dict.items() if not value]
        layers.append(initial_layer)

        # Keep track of processed elements
        processed = set(initial_layer)
        while True:
            next_layer = []
            for key, value in dependencies_dict.items():
                if key not in processed and all(dep in processed for dep in value):
                    next_layer.append(key)

            if not next_layer:
                break
            layers.append(next_layer)
            processed.update(next_layer)
        return layers
    except Exception as e:
        print("Error in generate_flow_layers: " + str(e))
        return []

