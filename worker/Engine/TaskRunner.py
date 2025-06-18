import Utils.utils as utils
from Utils.Timer import Timer
from Utils.constants import *

class TaskRunner(object):
        def __init__(self, task_dict, environment_key):
            self.node_key = task_dict['node_key']
            self.project_key = task_dict['project_key']
            self.code_to_run = task_dict['code_to_run']
            self.environment_key = environment_key
            self.extra_dict = {"node_key": self.node_key, "project_key": self.project_key, "environment_key": self.environment_key, IS_SYSTEM_TASK: True}
            self.extra_dict_exec = {"node_key": self.node_key, "project_key": self.project_key, "environment_key": self.environment_key, IS_SYSTEM_TASK: False}

        # Custom print function to log messages
        def custom_print(self, *args, sep=" ", end="\n", file=None, flush=False):
            full_message = sep.join(map(str, args))  # Convert all arguments to a string and join with sep
            utils.logger.info(full_message, extra=self.extra_dict_exec)

        def run_code(self):
            namespace = {}
            try:
                import waveassist
                waveassist.set_worker_defaults(ACCOUNT_ID, self.project_key, self.environment_key)

                # Inject the custom print function into the namespace
                namespace['print'] = self.custom_print

                # Try to compile the provided code to check for syntax errors
                compiled_code = compile(self.code_to_run, "<string>", "exec")

                # Execute the compiled code in the given namespace
                exec(compiled_code, namespace)

                # Ensure that the desired function is available in the namespace
                if 'run_task' not in namespace or not callable(namespace['run_task']):
                    raise NameError("'run_task' is not defined or is not callable in the provided code.")

                # Call the function and return the result
                result = namespace['run_task']()
                return True
            except SyntaxError as e:
                utils.logger.info("Syntax error in the provided code: " + str(e), extra=self.extra_dict)
                return False
            except NameError as e:
                utils.logger.info("Name error in the provided code: " + str(e), extra=self.extra_dict)
                return False
            except Exception as e:
                utils.logger.info("An error occurred: " + str(e), extra=self.extra_dict)
                return False

        def run(self):
            utils.logger.info("Starting Node: " + str(self.node_key), extra=self.extra_dict)
            timer = Timer(str(self.node_key))
            timer.start()
            result = self.run_code()
            timer.print_elapsed()
            utils.logger.info("Completed Node: " + str(self.node_key), extra=self.extra_dict)
            return result




