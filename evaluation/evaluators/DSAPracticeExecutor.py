import html
import re
from evaluation.evaluators.AnswerEvaluator import AnswerEvaluator
from evaluation.models import UserEvalQuestionAttempt
from services.glot_service import GlotService, TLEException
import logging

logger = logging.getLogger(__name__)

class DSAPracticeExecutor(AnswerEvaluator):
    def __init__(self, question_attempt: UserEvalQuestionAttempt, test_cases, language, code, main_code,output_seperator="\n"):
        super().__init__(question_attempt)
        self.test_cases = test_cases
        self.glot_service = GlotService()
        self.language = language
        self.code = code
        self.main_code = main_code
        self.output_separator = output_seperator

    def evaluate(self):
        """
            While calling the evaluate method, we are retrieving driver function which includes main function code 
            which is stored along with the question. This is retrieved from question data based on language selected by the user. 
            This main code is passed here so that we can replace the text {{middle_code}} from main function code with 
            actual user code. This will make code complete and make it executable for glot.
            This design is based on how geekforgeeks runs its evaluation.
            
            
            There is an edge case in glot for python. If number of testcases are larger and code breaks while executing testcases
            the following error occurs - 
            {'stdout': '', 'error': 'Error while executing command. Failed to write to stdin. Broken pipe (os error 32)', 'stderr': ''}
            
            In this case, we have to first check if this error is getting casued for current problem and its testcases.
            If problem causes then we have to divide the testcases in batch of 30 create input strings for them and call glot multiple times.
            
            If problem does not cause then we will pass all test cases in single input string and call glot only once.
        """
        file_name = self._extract_file_name()
        self.code = self.main_code.replace("{{ middle_code }}", self.code)

        eval_data = {"test_cases": []}
        batch_mode_enabled = False

        input_str = self._construct_input_string(self.test_cases)
        #First of all we have to check if there is error of win 32
        try:
            response = self.glot_service.get_execution_result(
                language=self.language, code=self.code, file_name=file_name, inputs=input_str
            )

            # Enable batch mode if error is : Error while executing command. Failed to write to stdin. Broken pipe (os error 32)
            if "Error while executing command. Failed to write to stdin." in response.get("error", ""):
                #if error : Error while executing command. Failed to write to stdin. Broken pipe (os error 32) occurs enable batch mode
                batch_mode_enabled = True

        except TLEException:
            self._handle_execution_error(eval_data, "Time Limit Exceeded")
            return
        except Exception as e:
            self._handle_execution_error(eval_data, "Something Went Wrong")
            logger.error(f"Unexpected error in DSA Execution - {e}")
            return

        if batch_mode_enabled:
            logging.info("Execution in batch mode")
            self._evaluate_in_batches(file_name, eval_data)
        else:
            logging.info("Execution in single mode")
            self._evaluate_single(response, eval_data)

        self.question_attempt.eval_data = eval_data
        self.question_attempt.status = UserEvalQuestionAttempt.Status.ATTEMPTED
        self.question_attempt.save()

    def _extract_file_name(self):
        """Extract the file name for Java classes."""
        if self.language == "java":
            match = re.search(r'class (\w+)(?:(?!\bclass\b).)*?public static void main', self.main_code, re.DOTALL)
            return match.group(1) if match else "Main"
        return "Main"

    def _construct_input_string(self, test_cases):
        """Construct the input string for execution from test cases."""
        return f"{len(test_cases)}\n" + "\n".join(tc["testCase"] for tc in test_cases) + "\n"

    def _handle_execution_error(self, eval_data, error_type):
        """Handle execution errors by updating eval_data and status."""
        eval_data["test_cases"] = [{'error': f'The code execution time exceeded the allowed limit. Please optimize your code for better performance.', 'error_type': error_type}]
        self.question_attempt.eval_data = eval_data
        self.question_attempt.status = UserEvalQuestionAttempt.Status.ATTEMPTED
        self.question_attempt.save()
    
    def _evaluate_in_batches(self, file_name, eval_data):
        """Evaluate test cases in batches of up to 8000 characters and break at testcase where actual error is occurring."""
        max_chars = 8000
        current_batch = []
        current_batch_input = ""
        total_chars = 0

        for test_case in self.test_cases:
            input_str = self._construct_input_string([test_case])
            input_length = len(input_str)

            if total_chars + input_length > max_chars:
                try:
                    response = self.glot_service.get_execution_result(
                        language=self.language, code=self.code, file_name=file_name, inputs=current_batch_input
                    )
                    error = response["stderr"]
                    logging.info(f"Batch Response: {response}")
                    self._process_outputs(current_batch, response, eval_data, error)
                    
                    # Exit if any test case failed in a batch. Don't execute further test cases in batches.
                    if any(not case["passed"] for case in eval_data["test_cases"]):
                        break
                except TLEException:
                    self._handle_execution_error(eval_data, "Time Limit Exceeded")
                    return
                
                # Reset batch and character count
                current_batch = []
                current_batch_input = ""
                total_chars = 0

            current_batch.append(test_case)
            current_batch_input += input_str
            total_chars += input_length

        # Process any remaining test cases in the last batch
        if current_batch:
            try:
                response = self.glot_service.get_execution_result(
                    language=self.language, code=self.code, file_name=file_name, inputs=current_batch_input
                )
                error = response["stderr"]
                logging.info(f"Batch Response: {response}")
                self._process_outputs(current_batch, response, eval_data, error)
            except TLEException:
                self._handle_execution_error(eval_data, "Time Limit Exceeded")
                return

        # Once error in batch occurred add remaining test cases with status as not evaluated
        remaining_batches = self.test_cases[len(current_batch):]
        for remaining_case in remaining_batches:
            original_inputs = remaining_case['testCase']
            expected_output = remaining_case["expectedOutput"].strip()

            eval_data["test_cases"].append({
                "passed": False,  # False as they haven't been run
                "inputs": original_inputs,
                "output": "",  # No output since they were not executed
                "error": "Not Evaluated",
                "error_type": "Not Evaluated",
                "expected": expected_output
            })



    def _evaluate_single(self, response, eval_data):
        """Evaluate all test cases in a single run."""
        outputs = response["stdout"].strip().split(self.output_separator) if response.get("stdout") else []
        error = response["stderr"]
        self._process_outputs(self.test_cases, response, eval_data, error)

    def _process_outputs(self, test_cases, response, eval_data, error=None):
        """Process outputs and compare with expected outputs."""
        outputs = response["stdout"].strip().split(self.output_separator) if response.get("stdout") else []
        error_type = "Runtime Error" if error else None

        # Handle case where the number of test cases and outputs do not match
        if len(test_cases) != len(outputs):
            self._handle_mismatched_outputs(test_cases, outputs, eval_data, error)
        else:
            for j, test_case in enumerate(test_cases):
                original_inputs = test_case['testCase']
                expected_output = test_case["expectedOutput"].strip()
                output = outputs[j].strip() if j < len(outputs) else ""
                passed = output == expected_output

                eval_data["test_cases"].append({
                    "passed": passed,
                    "inputs": original_inputs,
                    "output": output,
                    "error": error,
                    "error_type": error_type,
                    "expected": expected_output
                })

    def _handle_mismatched_outputs(self, test_cases, outputs, eval_data, error):
        """Handle scenarios where the number of test cases and outputs do not match. In case of runtime error in code glot returns ['']"""
        if len(outputs) == 1 or error:
            error_occured=error
            for j, test_case in enumerate(test_cases):
                original_inputs = test_case['testCase']
                expected_output = test_case["expectedOutput"].strip()
                if j < len(outputs):
                    output = outputs[j]
                    error=""
                    error_type=None
                else:
                    output = ""
                    error=error_occured
                    error_type="Runtime error"
                output = outputs[j].strip() if j < len(outputs) else ""
                passed = output == expected_output
                eval_data["test_cases"].append({
                    "passed": passed,
                    "inputs": original_inputs,
                    "output": output,
                    "error": error,
                    "error_type": error_type,
                    "expected": expected_output
                })
        else:
            """In case user adds print statements in code, causes outputs and number of testcases to mismatch so if no error in code then it is due to print statements"""
            expected_outputs = [tc["expectedOutput"].strip() for tc in test_cases]
            eval_data["test_cases"].append({
                "error": f'''Unexpected output detected. Please ensure your code does not contain unnecessary print statements.
                Output Generated For Example Test Case:
                {outputs[0]}
                Expected Output For Example Test Case:
                {expected_outputs[0]}''',
                "error_type": 'Unexpected Output Detected'
            })
            logging.info(f'Mismatched number of test cases and outputs: {len(test_cases)} vs {len(outputs)}')
