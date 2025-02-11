import re
import typing
from datetime import datetime
import random
from string import Template
import logging
import json
from openai import OpenAI
from OpenAIService.llm_classes.LLMConfig import GLOBAL_LOADED_LLM_CONFIGS, LLMConfig
from OpenAIService.models import OpenAIAssistant, PromptTemplate, ChatHistory,Tool, KnowledgeRepository, ContentReference
from OpenAIService.openai_service import OpenAIService
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenAIAssistantRepository:
    @staticmethod
    def get_assistant(name):
        """Created a fixture, from where we will store details about the assistant in DB.
            In this function just checking if id of assistant exists or not. If it doesn't
            exists create new id and store it for that assistant
        """
        try:
            assistant_from_db = OpenAIAssistant.objects.get(name=name)

            if assistant_from_db.assistant_id == '':
                new_assistant = OpenAIService().create_assistant(
                    name=assistant_from_db.name,
                    instructions=assistant_from_db.instructions,
                    tools=assistant_from_db.tools,
                    model=assistant_from_db.open_ai_model
                )

                assistant_from_db.assistant_id = new_assistant.id
                assistant_from_db.save()

                return new_assistant
            else:
                new_assistant = OpenAIService().get_assistant(id=assistant_from_db.assistant_id)
                return new_assistant


        except OpenAIAssistant.DoesNotExist:
            logging.error(f"Assistant not found for name: {name}")
            return None


class ValidLLMConfigs:
    AzureOpenAILLMConfig = 'AzureOpenAILLMConfig'

    @classmethod
    def get_all_valid_llm_configs(cls) -> list:
        return GLOBAL_LOADED_LLM_CONFIGS.keys()

    @classmethod
    def get_all_llm_configs_from_db(cls) -> list:
        return PromptTemplate.objects.all().values_list('llm_config_name', flat=True)

    @classmethod
    def check_llm_configs_in_db(cls) -> bool:
        llm_configs_in_db = ValidLLMConfigs.get_all_llm_configs_from_db()
        loaded_configs = cls.get_all_valid_llm_configs()
        missing_config_names = [config_name for config_name in loaded_configs if config_name not in llm_configs_in_db]
        if missing_config_names:
            raise ValueError(
                f"The following configs are missing from the configuration, but defined in DB: {missing_config_names} "
                f"To fix this, create these <name>.yaml files in {settings.LLM_CONFIGS_PATH} and restart the application.")
        return True


class ValidPromptTemplates:
    DEMO_PROMPT = "demo_prompt"
    ANOTHER_PROMPT = "another_prompt"
    CODE_REVISION_PROMPT = "code_revision_prompt"
    TEST_PROMPT = "test_prompt"
    DSA_PRACTICE = "dsa_practice_prompt"
    DOUBT_SOLVING = "doubt_solving"
    DOUBT_SOLVING_JSON = "doubt_solving_json"
    ASSISTANT_PROMPT = "assistant_prompt"
    CODE_QUALITY_PROCESSOR = "code_quality_processor"
    CODE_EFFICIENCY_PROCESSOR = "code_efficiency_processor"
    CODE_IMPROVEMENT_PROCESSOR = "code_improvement_processor"
    CODE_REVISION_TOPIC_PROCESSOR = "code_revision_topic_processor"
    CODE_SUMMARY_PROCESSOR = "code_summary_processor"
    APPROACH_CODE_SUMMARY_PROCESSOR = "approach_code_summary_processor"
    SENTIMENT_PROCESSOR = "sentiment_processor"
    COHERENCE_PROCESSOR = "coherence_processor"
    GRAMMAR_PROCESSOR = "grammar_processor"

    @classmethod
    def get_all_valid_prompts(cls) -> list:
        return [cls.TEST_PROMPT, cls.DSA_PRACTICE, cls.DOUBT_SOLVING, cls.DOUBT_SOLVING_JSON]

    @classmethod
    def get_all_prompts_from_db(cls) -> list:
        return PromptTemplate.objects.all().values_list('name', flat=True)

    @classmethod
    def check_prompts_in_db(cls) -> bool:
        db_prompts = ValidPromptTemplates.get_all_prompts_from_db()
        code_prompts = cls.get_all_valid_prompts()
        missing_prompts = [prompt for prompt in code_prompts if prompt not in db_prompts]
        if missing_prompts:
            raise ValueError(f"The following prompts are missing from the database: {missing_prompts}. "
                             f"To fix this, set DISABLE_PROMPT_VALIDATIONS to True, start application and create these "
                             f"prompt templates in DB.")
        return True


class PromptTemplateRepository:
    @staticmethod
    def get_by_name(name):
        try:
            prompt_template = PromptTemplate.objects.get(name=name)
            return prompt_template
        except PromptTemplate.DoesNotExist:
            return None


class ChatHistoryRepository:

    def __init__(self, chat_history_id: int | None) -> None:
        if chat_history_id is None:
            self.chat_history_obj = ChatHistory.objects.create()
        else:
            self.chat_history_obj = ChatHistory.objects.get(id=chat_history_id)

    @staticmethod
    def create_new_chat_history(*, initialize=True) -> ChatHistory:
        self_instance = ChatHistoryRepository(chat_history_id=None)
        if initialize:
            pass
        
    def is_chat_history_empty(self):
        return len(self.chat_history_obj.chat_history) == 0

    def commit_chat_to_db(self):        
        self.chat_history_obj.save()

    @staticmethod
    def _generate_12_digit_random_id():
        min_num = 10 ** 11
        max_num = (10 ** 12) - 1
        return random.randint(min_num, max_num)

    def add_msgs_to_chat_history(self, msg_list: typing.List, timestamp: float = None, commit_to_db: bool = False) -> None:
        if not timestamp:
            timestamp = round(datetime.now().timestamp(), 1)
        for msg in msg_list:
            msg["timestamp"] = timestamp
            msg["id"]= self._generate_12_digit_random_id(),
        self.chat_history_obj.chat_history.extend(msg_list)
        if commit_to_db:
            self.commit_chat_to_db()

    def _add_user_msg_to_chat_history(self, *, msg_content: str, msg_timestamp: float) -> None:
        self._add_msg_to_chat_history(msg_content=msg_content, msg_type="user",
                                      msg_timestamp=msg_timestamp)

    def get_msg_list_for_llm(self) -> list:
        msg_list = []
        for msg in self.chat_history_obj.chat_history:
            if msg["role"] in ["user", "assistant", "system"]:
                new_msg = {"content": msg["content"], "role": msg["role"]}
            elif msg["role"] == "tool":
                new_msg = {"content": msg["content"],
                           "role": "tool",
                           "tool_call_id": msg["tool_call_id"],
                           "name": msg["name"]
                           }
            else:
                raise ValueError(f"Unexpected msg role: {msg['role']}")

            if "tool_calls" in msg:
                new_msg["tool_calls"] = msg["tool_calls"]
            msg_list.append(new_msg)
        return msg_list

    def add_or_update_system_msg(self, new_system_msg):
        if len(self.chat_history_obj.chat_history) > 0:
            if self.chat_history_obj.chat_history[0]["role"] == "system":
                self.chat_history_obj.chat_history[0]["content"] = new_system_msg
            else:
                raise ValueError(f"Unexpected: First msg is not a system msg. Chat id: {self.chat_history_obj.id}")
        else:
            self.chat_history_obj.chat_history = [{"role": "system", "content": new_system_msg}]

    @staticmethod
    def get_chat_history_by_chat_id(chat_id):
        try:
            chat_history_obj = ChatHistory.objects.get(chat_id=chat_id)
            return chat_history_obj.id
        except ChatHistory.DoesNotExist:
            return None



class LLMCommunicationWrapper:
    @staticmethod
    def convert_to_function(source_code: str):
        match = re.search(r'def\s+(\w+)\s*\(', source_code)
        if match:
            function_name = match.group(1)
        else:
            raise ValueError("No valid function definition found in the provided source code.")
        # Execute the source code in the current local scope
        exec(source_code, locals())
        # Retrieve and return the function by the extracted name
        return locals()[function_name]

    @staticmethod
    def package_function_response(was_success, response_string, timestamp=None):
        # formatted_time = get_local_time() if timestamp is None else timestamp
        packaged_message = {
            "status": "OK" if was_success else "Failed",
            "message": response_string,
            # "time": formatted_time,
        }

        return json.dumps(packaged_message, ensure_ascii=False)

    @staticmethod
    def parse_json(string) -> dict:
        """Parse JSON string into JSON with both json and demjson"""
        result = None
        try:
            result = json.loads(string, strict=True)
            return result
        except Exception as e:
            print(f"Error parsing json with json package: {e}")
            raise e
        # try:
        #     result = demjson.decode(string)
        #     return result
        # except demjson.JSONDecodeError as e:
        #     print(f"Error parsing json with demjson package: {e}")
        #     raise e

    @staticmethod
    def get_tool_context_params(tool_function_name, context_vars,context_params):
        context_params_json = {}
        for key in context_params:
            formatted_key = f'{key.strip("__")}'
            if formatted_key in context_vars:
                context_params_json[key] = context_vars[formatted_key]
            else:
                logger.error(f"Key '{key}' from context_params of tool not found in context_vars")
        return context_params_json

    def get_chat_history_object(self):
        return self.chat_history_repository.chat_history_obj

    def __init__(self, *, prompt_name, chat_history_id=None, assistant_id=None,
                 initialize=True, initializing_context_vars=None):
        self.prompt_name = prompt_name
        self.prompt_template = PromptTemplate.objects.get(name=prompt_name)
        self.chat_history_repository = ChatHistoryRepository(chat_history_id=chat_history_id)

        self.tool_json_specs = [{"type": "function", "function": tool.tool_json_spec} for tool in
                                self.prompt_template.tools.all()]
        self.tool_callables = {tool.name: LLMCommunicationWrapper.convert_to_function(tool.tool_code) for tool in
                               self.prompt_template.tools.all()}
        self.context_params = {tool.name: tool.context_params for tool in self.prompt_template.tools.all()}

<<<<<<< HEAD
        print(GLOBAL_LOADED_LLM_CONFIGS)
        llm_config_instance: LLMConfig = GLOBAL_LOADED_LLM_CONFIGS[self.prompt_template.llm_config_name]
=======
        self.llm_config_name = random_llm_config_name

        llm_config_instance: LLMConfig = GLOBAL_LOADED_LLM_CONFIGS[self.llm_config_name]
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)
        self.llm_config_params = llm_config_instance.get_config_dict()
        
        if llm_config_instance.__class__.__name__ == "OpenAIAssistantConfig":

            if assistant_id is None:
                raise ValueError("Assistant ID is required in OpenAIAssistantConfig")
            self.client = OpenAI(api_key=self.llm_config_params['api_key'])
            self.assistant_id = assistant_id
            if self.chat_history_repository.chat_history_obj.thread_id is None:
                thread = self.client.beta.threads.create()
                self.chat_history_repository.chat_history_obj.thread_id = thread.id
                self.thread_id=thread.id
                self.chat_history_repository.commit_chat_to_db()
            else:
                self.thread_id = self.chat_history_repository.chat_history_obj.thread_id
                
                
        if llm_config_instance.are_tools_enabled() and len(self.tool_json_specs):
            self.llm_config_params["tools"] = self.tool_json_specs
                        
        elif len(self.tool_json_specs):
<<<<<<< HEAD
            raise ValueError(f"Tools not enabled in LLM config but used in LLM Prompt - {self.prompt_name}. "
                             f"LLM config name - {llm_config_instance.name}")
=======
            raise ValueError(
                f"Tools not enabled in LLM config but used in LLM Prompt - {self.prompt_name}. "
                f"LLM config name - {llm_config_instance.name}"
            )

    def __init__(
        self,
        *,
        prompt_name,
        chat_history_id=None,
        assistant_id=None,
        initialize=True,
        initializing_context_vars=None,
        response_format_class: type[BaseModel] | None = None,
    ):
        self.prompt_name = prompt_name
        self.response_format_class = response_format_class
        self.prompt_template = PromptTemplate.objects.get(name=prompt_name)
        self.chat_history_repository = ChatHistoryRepository(
            chat_history_id=chat_history_id
        )

        self.tool_json_specs = [
            {"type": "function", "function": tool.tool_json_spec}
            for tool in self.prompt_template.tools.all()
        ]
        self.tool_callables = {
            tool.name: LLMCommunicationWrapper.convert_to_function(tool.tool_code)
            for tool in self.prompt_template.tools.all()
        }
        self.context_params = {
            tool.name: tool.context_params for tool in self.prompt_template.tools.all()
        }

        self.assistant_id = assistant_id

        self.llm_config_names = [
            config.name for config in self.prompt_template.llm_config_names.all()
        ]
        self.init_llm_config()

>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)
        self.to_be_logged_context_vars = self.prompt_template.logged_context_vars
        if initialize:
            if chat_history_id is not None:
                logger.error("Cannot initialize chat history if chat history is already created. Not initializing")
            else:
                self.initialize_chat_history(initializing_context_vars=initializing_context_vars, commit_to_db=True)

    def get_llm_config(self)->dict:
        return self.llm_config_params

    def get_initial_msg_templates(self):
        return self.prompt_template.initial_messages_templates

<<<<<<< HEAD
    def initialize_chat_history(self, *, initializing_context_vars=None, commit_to_db=True):
        if initializing_context_vars is None:
            initializing_context_vars = {}
        system_prompt = Template(self.prompt_template.system_prompt_template).substitute(initializing_context_vars)
        init_msg_list = [{"role": "system", "content": system_prompt}]
        for msg in self.prompt_template.initial_messages_templates:
            init_msg_list.append({"content": Template(msg["content"]).substitute(initializing_context_vars),
                                  "role": msg["role"],
                                  "system_generated": True,
                                  "show_in_user_history": False,
                                  })
=======
    @staticmethod
    def get_chat_history_init_msg_list(prompt_template, initializing_context_vars):
        if initializing_context_vars is None:
            initializing_context_vars = {}
        system_prompt = Template(prompt_template.system_prompt_template).substitute(
            initializing_context_vars
        )
        init_msg_list = [{"role": "system", "content": system_prompt}]
        for msg in prompt_template.initial_messages_templates:
            init_msg_list.append(
                {
                    "content": Template(msg["content"]).substitute(
                        initializing_context_vars
                    ),
                    "role": msg["role"],
                    "system_generated": True,
                    "show_in_user_history": False,
                }
            )
        return init_msg_list

    def initialize_chat_history(
        self, *, initializing_context_vars=None, commit_to_db=True
    ):
        init_msg_list = LLMCommunicationWrapper.get_chat_history_init_msg_list(
            self.prompt_template, initializing_context_vars
        )
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)
        self.chat_history_repository.add_msgs_to_chat_history(init_msg_list)
        if commit_to_db:
            self.chat_history_repository.commit_chat_to_db()

    def handle_tool_call(self, choice_from_llm,context_vars):
        if choice_from_llm["message"].get("tool_calls") is None:
            return {}
        tool_call_message = choice_from_llm["message"]
        tool_call_instancd = tool_call_message["tool_calls"][0]
        result = tool_call_instancd["function"]
        tool_call_id = tool_call_instancd["id"]
        tool_function_name = result.get("name", None)
        if tool_function_name not in self.tool_callables:
            logger.error(
                f"Unexpected tool call - {tool_function_name}. Chat id - {self.chat_history_repository.chat_history_obj.id}")
            return {}
        json_tool_function_params = result.get("arguments", {})
        tool_function_params = LLMCommunicationWrapper.parse_json(json_tool_function_params)
        context_params = self.context_params[tool_function_name]
        # Initialize context_params_json as an empty dictionary
        context_params_json = LLMCommunicationWrapper.get_tool_context_params(tool_function_name, context_vars,context_params)
        try:
            tool_output = self.tool_callables[tool_function_name](**context_params_json,**tool_function_params)
            logger.info(f"Got tool output of {tool_function_name} - {tool_output}")
            tool_output_packaged = LLMCommunicationWrapper.package_function_response(True, str(tool_output))
            logger.info(f"Generated packaged tool response = f{tool_output_packaged}")
        except Exception as exc:
            logger.error(f"Error in tool call - {exc}. Chat id - {self.chat_history_repository.chat_history_obj.id}")
            tool_output_packaged = LLMCommunicationWrapper.package_function_response(False, "Got error in tool call")

        tool_call_msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [tool_call_instancd.dict()],
            "tool_call_id": tool_call_id,
        }
        
        our_tool_response = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_function_name,
            "content": tool_output_packaged
        }
        existing_msg_list = self.chat_history_repository.get_msg_list_for_llm()
        new_msg_list = existing_msg_list + [tool_call_msg, our_tool_response]
        a_time = datetime.now().timestamp()
        post_tool_call_response = OpenAIService.send_messages_and_get_response(new_msg_list, self.llm_config_params)
        post_tool_call_response_dict = {
            "role": "assistant",
            "message_generation_time": round(datetime.now().timestamp() - a_time, 1),
            "content": post_tool_call_response["message"]["content"],
        }
        tool_call_msg['context_params']=context_params_json
        self.chat_history_repository.add_msgs_to_chat_history(
            [tool_call_msg, our_tool_response, post_tool_call_response_dict])
        self.chat_history_repository.commit_chat_to_db()
        tool_data = {
                        "used_tool": tool_function_name,
                        "tool_calls": [tool_call_instancd.dict()],
                        "tool_content": tool_output_packaged
                    }
        modified_message_content = {"type":"bot","message":post_tool_call_response["message"]["content"],"tool_data":tool_data}
        return modified_message_content


    def get_one_time_completion(self, kwargs):
        # Fetch the prompt template from the database by name
        prompt_template = PromptTemplate.objects.get(name=self.prompt_name)

        required_keys = prompt_template.required_kwargs

        # Check if all required keys are present in kwargs
        missing_keys = [key for key in required_keys if required_keys[key] and key not in kwargs]
        if missing_keys:
            error_message = f"Missing required keys: {', '.join(missing_keys)}"
            logging.error(error_message)
            raise ValueError(error_message)

        # Access system_prompt and user_prompt fields
        system_prompt = prompt_template.system_prompt_template
        user_prompt = prompt_template.system_prompt_template

        # Substitute values in the prompts using kwargs
        formatted_system_prompt = system_prompt
        formatted_user_prompt = user_prompt

        for key, value in kwargs.items():
            formatted_system_prompt = formatted_system_prompt.replace(f"${key}", str(value))
            formatted_user_prompt = formatted_user_prompt.replace(f"${key}", str(value))

        combined_prompt = {'system_prompt': formatted_system_prompt, 'user_prompt': formatted_user_prompt}

        return combined_prompt

    def get_final_user_message(self, user_msg: str, context_vars=None) -> dict:
        user_prompt = user_msg
        if self.prompt_template.user_prompt_template:
            user_prompt = Template(self.prompt_template.user_prompt_template).substitute(**context_vars, user_msg=user_msg)
        return {"role":"user", "content":user_prompt}

<<<<<<< HEAD
    def send_user_message_and_get_response(self, user_msg: str, context_vars=None) -> str:
=======
    @staticmethod
    def get_response_without_chathistory(
        prompt_name,
        response_format_class=None,
        initializing_context_vars=None,
        retry_on_openai_time_limit=False,
    ):
        def select_llm_config(llm_config_names):
            random_llm_config_name = random.choice(llm_config_names)
            llm_config_instance: LLMConfig = GLOBAL_LOADED_LLM_CONFIGS[
                random_llm_config_name
            ]
            return llm_config_instance.get_config_dict(), random_llm_config_name

        prompt_template = PromptTemplate.objects.get(name=prompt_name)

        llm_config_names = [
            config.name for config in prompt_template.llm_config_names.all()
        ]
        if len(llm_config_names) == 0:
            raise LLMCommunicationWrapper.LLMConfigsNotAvailable()

        llm_config_params, llm_config_name = select_llm_config(llm_config_names)

        msg_list = LLMCommunicationWrapper.get_chat_history_init_msg_list(
            prompt_template, initializing_context_vars
        )

        while True:
            try:
                choice_response = OpenAIService.send_messages_and_get_response(
                    messages=msg_list,
                    llm_config_params=llm_config_params,
                    response_format_class=response_format_class,
                )
                break
            except openai._exceptions.RateLimitError as e:
                if retry_on_openai_time_limit:
                    llm_config_names.remove(llm_config_name)
                    llm_config_params, llm_config_name = select_llm_config(
                        llm_config_names
                    )
                else:
                    raise e

        response_msg_content = choice_response["message"]["content"]

        return response_msg_content

    def send_user_message_and_get_response(
        self,
        user_msg: str,
        context_vars=None,
        retry_on_openai_time_limit=False,
    ) -> str:
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)
        if context_vars is None:
            context_vars = {}

        required_keys = self.prompt_template.required_kwargs
        missing_keys = [key for key in required_keys if key not in context_vars]
        logged_context_vars = self.prompt_template.logged_context_vars
        logger.info(f"Required keys: {required_keys}. Missing keys: {missing_keys}.")
        if missing_keys:
            error_message = f"Missing required keys: {', '.join(missing_keys)}"
            raise ValueError(error_message)
        
        filtered_context_vars = {key: value for key, value in context_vars.items() if key in logged_context_vars}
        self.update_chat_history(context_vars)
        new_msg_list = self.chat_history_repository.get_msg_list_for_llm()
        new_msg_list += [self.get_final_user_message(user_msg, context_vars=context_vars)]

        # The user msg is added here, but in case of tool call we are committing to db only post handling of tool
        # call. ALSO, User msg in history and the one sent to llm finally are intentionally different
        self.chat_history_repository.add_msgs_to_chat_history(
            [{"role": "user", "content": user_msg, "context_vars": filtered_context_vars}])
        a_time = datetime.now().timestamp()
        choice_response = OpenAIService.send_messages_and_get_response(new_msg_list, self.llm_config_params)

        if choice_response["message"].get("tool_calls") is not None:
            return self.handle_tool_call(choice_response,context_vars)
        else:
            response_msg_content = choice_response["message"]["content"]
<<<<<<< HEAD
            self.chat_history_repository.add_msgs_to_chat_history(
                [{"role": "assistant",
                  "message_generation_time": round(datetime.now().timestamp() - a_time,1),
                  "content": response_msg_content}])
            self.chat_history_repository.commit_chat_to_db()
            return response_msg_content
=======
            msg_id = self.chat_history_repository.add_msgs_to_chat_history(
                [
                    {
                        "role": "assistant",
                        "message_generation_time": round(
                            datetime.now().timestamp() - a_time, 1
                        ),
                        "content": response_msg_content,
                    }
                ]
            )[0][0]

            self.chat_history_repository.commit_chat_to_db()
            response = {"message": response_msg_content, "id": msg_id}
            return response
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)

    def update_chat_history(self, context_vars: None):
        if context_vars is None:
            context_vars = {}
        is_chat_history_empty = self.chat_history_repository.is_chat_history_empty()
        system_prompt = Template(self.prompt_template.system_prompt_template).substitute(**context_vars)

        if not is_chat_history_empty:
            self.chat_history_repository.add_or_update_system_msg(system_prompt)
        else:
            self.initialize_chat_history(initializing_context_vars=context_vars, commit_to_db=False)
            # init_msg_list = [{"role": "system", "content": system_prompt}]
            # for msg in self.prompt_template.initial_messages_templates:
            #     init_msg_list.append({"content": Template(msg["content"]).substitute(**context_vars),
            #                           "role": msg["role"],
            #                           "system_generated":True,
            #                           "show_in_user_history": False,
            #                           })
            # self.chat_history_repository.add_msgs_to_chat_history(init_msg_list)
    

    @staticmethod
<<<<<<< HEAD
    def get_processed_chat_messages(chat_history,is_superuser):
=======
    def update_message_thumb_rating(chat_history_obj, message_id, thumb):
        for msg in chat_history_obj.chat_history:
            if msg.get("id") and msg["id"][0] == message_id:
                msg["thumb"] = thumb
                chat_history_obj.save()
                return True
        return False

    @staticmethod
    def get_processed_chat_messages(chat_history, is_superuser):
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)
        messages_list = []  # Initialize list to store processed messages
        mapping = {"user": "user", "assistant": "bot"}
        for i, msg in enumerate(chat_history):
            if msg.get("show_in_user_history", True) == False:
                    continue
            # Check if the message role is valid and it is not a tool call or initial message
            if msg["role"] in mapping and not msg.get("tool_calls") and not msg.get("initial_message", None):
                msg_type = mapping[msg["role"]]  # Map the role to its type
                message_content = msg["content"]
                extra = {}  # Initialize extra information dictionary

                # If the user is a superuser, include tool information
                if is_superuser and i > 0 and chat_history[i-1]["role"] == "tool":
                    used_tool = chat_history[i-1]["name"]
                    tool_calls = chat_history[i-2].get("tool_calls", [])
                    content = chat_history[i-1]["content"]
                    extra = {
                        "used_tool": used_tool,
                        "tool_calls": tool_calls,
                        "tool_content": content
                    }

                # Append the message and additional information to the list
<<<<<<< HEAD
                messages_list.append({
                    "message": message_content,
                    "type": msg_type,
                    "tool_data": extra
                })
=======
                messages_list.append(
                    {
                        "message": message_content,
                        "type": msg_type,
                        "tool_data": extra,
                        "id": msg["id"][0],
                        "thumb": msg.get("thumb", None),
                    }
                )
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)

        return messages_list
    
    def _send_user_message(self, user_msg: str, context_vars=None) -> str:
        if context_vars is None:
            context_vars = {}

        # Check for required keys and log missing keys
        required_keys = self.prompt_template.required_kwargs
        print(self.prompt_template)
        missing_keys = [key for key in required_keys if key not in context_vars]
        logger.info(f"Required keys: {required_keys}. Missing keys: {missing_keys}.")
        if missing_keys:
            error_message = f"Missing required keys: {', '.join(missing_keys)}"
            raise ValueError(error_message)

        # Update chat history with user message
        filtered_context_vars = {key: value for key, value in context_vars.items() if key in self.prompt_template.logged_context_vars}
        # self.update_chat_history(context_vars)
        
        new_msg_list = self.chat_history_repository.get_msg_list_for_llm()
        new_msg_list += [self.get_final_user_message(user_msg, context_vars=context_vars)]
        print(new_msg_list)
        # The user msg is added here, but in case of tool call we are committing to db only post handling of tool
        # call. ALSO, User msg in history and the one sent to llm finally are intentionally different
        
        # Create a new user message in the thread
        
        # message = self.client.beta.threads.messages.create(
        #     thread_id=self.thread_id,
        #     role='user',
        #     content=Template(self.prompt_template.system_prompt_template).substitute(**context_vars)
        # )
        
        message = self.client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role='user',
            content=user_msg
        )
        
        # thread = self.client.beta.threads.create(
        #         messages=[
        #             {"role": "user", "content": Template(self.prompt_template.system_prompt_template).substitute(**context_vars)},
        #             {"role": "user", "content": user_msg}
        #         ]
        #     )
        return message

    def send_user_message_and_get_stream_response_from_assistant(self, user_msg: str, event_handler, context_vars=None, ) -> str:
        self._send_user_message(user_msg, context_vars)
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

    def send_user_message_and_get_response_from_assistant(self, user_msg: str, context_vars=None) -> str:
        self._send_user_message(user_msg, context_vars)
        
        # Start the run
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            additional_instructions=Template(self.prompt_template.system_prompt_template).substitute(**context_vars)
        )
        logger.info("Run started successfully.")

        # Wait for the run to complete
        while run.status not in ["completed", "failed", "canceled"]:
            run = self.client.beta.threads.runs.retrieve(thread_id=self.thread_id, run_id=run.id)
            logger.info("Waiting for run to complete...")
        # Check the status of the run
        if run.status == "completed":
            logger.info("Run completed successfully!")
        else:
            logger.error(f"Run {run.status.capitalize()}!")
            logger.error(f"Error Code: {run.last_error.code}, message: {run.last_error.message}")
            raise RuntimeError(f"Run failed with error code: {run.last_error.code}, message: {run.last_error.message}")

        # Retrieve messages from the thread
        messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)
        print(messages)
        # Find the assistant's response
        for message in messages.data:
            if message.role == 'assistant':
                response_content = message.content[0].text.value
                return response_content
              
    @staticmethod
    def get_processed_chat_messages_in_doubt_history(chat_history):
        messages_list = []  # Initialize list to store processed messages
        mapping = {"user": "user", "assistant": "assistant"}
        for i, msg in enumerate(chat_history):
            if msg.get("show_in_user_history", True) == False:
                continue
            # Check if the message role is valid and it is not a tool call or initial message
            if msg["role"] in mapping and not msg.get("tool_calls") and not msg.get("initial_message", None):
                msg_type = mapping[msg["role"]]  # Map the role to its type
                if msg_type =="assistant":
                    message_content = {'response':msg["content"]}
                    message_content = json.dumps(message_content)
                    message_content = message_content.replace("{","{{").replace("}","}}")
                elif msg_type == "user":
                    message_content=msg["content"]                
                timestamp=msg['timestamp']
                id=msg['id']
                messages_list.append({
                    "id":id,
                    "content": message_content,
                    "role": msg_type,
                    "timestamp": timestamp
                })

        return messages_list


class KnowledgeRepositoryRepository:
    @staticmethod
    def create_knowledge_repository(type_of_repo, source_path, source_type, index_path, sas_token):
        knowledge_repository =KnowledgeRepository(
            type_of_repo=type_of_repo,
            #organization=organization,
            #api_key=api_key,
            #course_id=course_id,
            source_path=source_path,
            source_type=source_type,
            index_path=index_path,
            sas_token=sas_token
        )
        knowledge_repository.save()
        return knowledge_repository


class ContentReferenceRepository:
    @staticmethod
    def create_content_reference(content_type, path, knowledge_repository_id):
        content_reference,created = ContentReference.objects.get_or_create(
            content_type=content_type,
            #course_id=course_id,
            path=path,
            knowledge_repository_id=knowledge_repository_id
        )

        return content_reference,created

    @staticmethod
    def get(id):
        return ContentReference.objects.get(id=id)
    
    @staticmethod
    def get_by_file_id(file_id):
        return ContentReference.objects.get(file_id=file_id)

    @staticmethod
    def get_all_references_by_knowledge_repository(knowledge_repository_id):
<<<<<<< HEAD
        return ContentReference.objects.filter(knowledge_repository_id_id=knowledge_repository_id)
=======
        return ContentReference.objects.filter(
            knowledge_repository_id_id=knowledge_repository_id
        )


class ABTestingLLMCommunicationWrapper(LLMCommunicationWrapper):

    def __init__(
        self,
        user_id,
        experiment_name=None,
        chat_history_id=None,
        default_prompt_template_name=None,
        initialize=True,
        initializing_context_vars=None,
        response_format_class: type[BaseModel] | None = None,
    ):
        # Take the values from the llm_config_v2 file
        self.posthog_api_key = settings.POSTHOG_API_KEY
        self.default_prompt_template_name = default_prompt_template_name
        # Initialize PostHog
        posthog.api_key = self.posthog_api_key
        posthog.host = "https://us.i.posthog.com"

        self.user_id = user_id  # Added to store user_id
        prompt_template_name = self.get_prompt_template_name_from_experiment(
            experiment_name
        )
        logger.info(f"Prompt template name from experiment: {prompt_template_name}")
        try:
            super().__init__(
                prompt_name=prompt_template_name,
                chat_history_id=chat_history_id,
                initialize=initialize,
                initializing_context_vars=initializing_context_vars,
                response_format_class=response_format_class,
            )
        except PromptTemplate.DoesNotExist:
            logger.error(
                f"Prompt template from experimentation does not exist. Prompt name: {prompt_template_name}"
            )
            super().__init__(
                prompt_name=default_prompt_template_name,
                chat_history_id=chat_history_id,
                initialize=initialize,
                initializing_context_vars=initializing_context_vars,
                response_format_class=response_format_class,
            )

    def get_prompt_template_name_from_experiment(self, experiment_name):
        try:
            # Fetch the feature flag value for the user
            feature_flag_variant_name = (
                ExperimentHelper().get_feature_flag_variant_name(
                    flag_key=experiment_name, user_id=self.user_id
                )
            )
            if not feature_flag_variant_name:
                logging.error(
                    f"Feature flag was returned None. User id: {self.user_id}, experiment name: {experiment_name}"
                )
                return self.default_prompt_template_name
            # feature_flag_payload = ExperimentHelper().get_feature_flag_payload(
            #     flag_key=experiment_name, user_id=self.user_id
            # )

            # prompt_template_name = feature_flag_payload.get("prompt_template_name") # type: ignore

            # Map feature flag value to experiment groups
            return feature_flag_variant_name
        except Exception as e:
            logging.error(f"Error determining experiment group from feature flag: {e}")
            return self.default_prompt_template_name
>>>>>>> 1e6f91b (Implement usage of LLMCommunicationWrapper with json mode in code processors)
