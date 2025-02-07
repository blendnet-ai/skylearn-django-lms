from django.db import models

from ..models import Question, UserEvalQuestionAttempt, AssessmentAttempt, AssessmentGenerationConfig
from ..repositories import AssessmentAttemptRepository, AssessmentGenerationConfigRepository
from ..usecases import AssessmentUseCase, XobinUseCase
from data_repo.repositories import ConfigMapRepository
import logging

logger = logging.getLogger(__name__)

class BaseAssessmentGenerationLogic:
    def __init__(self, assessment_generation_id):
        self.assessment_generation_id = assessment_generation_id
        self.assessment_config_data = AssessmentGenerationConfigRepository.return_assessment_generation_class_data(assessment_generation_id)
        self.kwargs = self.assessment_config_data.kwargs
        self.assessment_display_name = self.assessment_config_data.assessment_display_name

    def validate_kwargs(self):
        raise NotImplementedError("validate_kwargs method must be implemented in subclasses")

    def generate_assessment_attempt(self, user=None):
        raise NotImplementedError("generate_assessment_attempt method must be implemented in subclasses")


class TagBasedRandomAssessment(BaseAssessmentGenerationLogic):
    def __init__(self, assessment_generation_id):
        super().__init__(assessment_generation_id)

    def validate_kwargs(self):
        required_keys = ['tags', 'category', 'total_number','section_name', 'skippable']
        for key in required_keys:
            if key not in self.kwargs:
                return False, f"Missing required key: {key}"
        if not isinstance(self.kwargs['tags'], list):
            return False, "'tags' must be a list"
        for tag in self.kwargs['tags']:
            if not isinstance(tag, dict) or 'tag' not in tag or 'number' not in tag:
                return False, "Each tag in 'tags' must be a dictionary with 'tag' and 'number' keys"

        if not isinstance(self.kwargs['total_number'], int):
            return False, "'total_number' must be an integer"

        if not isinstance(self.kwargs['skippable'], bool):
            return False, "'skippable' must be a boolean"
        
        if not isinstance(self.kwargs['section_name'], str):
            return False, "'section_name' must be a string"
        
        return True

    def generate_assessment_attempt(self, user=None):
        if not self.validate_kwargs():
            raise ValueError("Invalid kwargs")

        category = self.kwargs.get('category')

        tags = self.kwargs.get('tags')
        total_number = self.kwargs.get('total_number')     
        section_name = self.kwargs.get('section_name')
        skippable = self.kwargs.get('skippable')
        question_data = AssessmentUseCase.fetch_question_ids_from_tag(category, total_number, tags, section_name, skippable)
        return question_data
    
class SubCategoryBasedRandomAssessment(BaseAssessmentGenerationLogic):
    def __init__(self, assessment_generation_id):
        super().__init__(assessment_generation_id)

    def validate_kwargs(self):
        required_keys = ['category', 'total_number', 'subcategories']
        for key in required_keys:
            if key not in self.kwargs:
                return False, f"Missing required key: {key}"

        if not isinstance(self.kwargs['total_number'], int):
            return False, "'total_number' must be an integer"

        subcategories = self.kwargs['subcategories']
        if not isinstance(subcategories, list):
            return False, "'subcategories' must be a list"

        for subcategory in subcategories:
             
            if not isinstance(subcategory, dict) or 'number' not in subcategory or 'sub_category' not in subcategory or 'skippable' not in subcategory:
                return False, "Each subcategory in 'subcategories' must be a dictionary with 'number' and 'sub_category'and 'skippable' keys"

            if not isinstance(subcategory['skippable'], bool):
                return False, "'skippable' must be a boolean"

            if not isinstance(subcategory['number'], int):
                return False, "'number' in each subcategory must be an integer"

        return True

    def generate_assessment_attempt(self, user=None):
        if not self.validate_kwargs():
            raise ValueError("Invalid kwargs")
        category = self.kwargs.get('category')
        subcategories = self.kwargs.get('subcategories')
        total_number = self.kwargs.get('total_number')
        question_data = AssessmentUseCase.fetch_question_ids_from_sub_category(category, total_number, subcategories)
    
        return question_data
    
class HardcodedQuestionsAssessment(BaseAssessmentGenerationLogic):
    def __init__(self, config):
        super().__init__(config)

    def validate_kwargs(self):
        # Assuming question_ids is a list of integers
        return all(isinstance(qid, int) for qid in self.question_ids)

    def generate_assessment_attempt(self, user=None):
        # Implement generation logic here
        pass

class XobinBasedAssessment(BaseAssessmentGenerationLogic):
    def __init__(self, config):
        super().__init__(config)

    def validate_kwargs(self):
        required_keys = ['assessment_id']
        for key in required_keys:
            if key not in self.kwargs:
                return False, f"Missing required key: {key}"

        if not isinstance(self.kwargs['assessment_id'], int):
            return False, "'assessment_id' must be an integer"
                
        return True

    def generate_assessment_attempt(self, user=None):
        if not self.validate_kwargs():
            raise ValueError("Invalid kwargs")
        assessment_id = self.kwargs.get('assessment_id')
        question_data = XobinUseCase.generate_xobin_assessment_url(user, assessment_id)
        
        return question_data


class MockInterviewBasedRandomAssessment(BaseAssessmentGenerationLogic):
    
    def __init__(self, assessment_generation_id, assessment_generation_details):
        super().__init__(assessment_generation_id)
        self.assessment_generation_details = assessment_generation_details
        self.role = assessment_generation_details.get('role',None) 
        self.difficulty = assessment_generation_details.get('difficulty_level',None) 
        self.config_data = self.get_assessment_generation_configs()
        self.valid_roles = self.get_valid_options_by_name('role')
        self.valid_difficulty_levels = self.get_valid_options_by_name('difficulty_level')
        self.required_keys = self.get_required_keys_from_config()

    @staticmethod
    def get_assessment_generation_configs():
        return ConfigMapRepository.get_config_by_tag(tag="Mock_Interview")


    
    def get_valid_options_by_name(self,name):
        options = []
        # Loop through each section in the config data
        for section in self.config_data[0].get('sections', []):
            # Check if the section's assessment_generation_config_id matches the desired id
            if section.get('assessment_generation_config_id') == self.assessment_generation_id:  # Adjust as needed
                # Loop through each field in the section
                for field in section.get('fields', []):
                    # Check if the field's name matches the input name
                    if field.get('name') == name:
                        options = field.get('options', [])
                        break  # Exit the loop once options are found
                if options:
                    break  # Exit outer loop if options are found
        labeled_options = [option['label'] for option in options]
        return labeled_options

    def get_required_keys_from_config(self):
        required_keys = []
        # Loop through each section in the config data
        for section in self.config_data[0].get('sections', []):
            # Check if the section's assessment_generation_config_id matches the desired id
            if section.get('assessment_generation_config_id') == self.assessment_generation_id:
                # Loop through each field in the section
                for field in section.get('fields', []):
                    if field.get('required', False):  # Check if the field is required
                        required_keys.append(field.get('name'))  # Add field name to required keys
        return required_keys

    def validate_kwargs(self):
        required_keys = ['category', 'total_number', 'subcategories']
        for key in required_keys:
            if key not in self.kwargs:
                return False, f"Missing required key: {key}"

        if not isinstance(self.kwargs['total_number'], int):
            return False, "'total_number' must be an integer"

        subcategories = self.kwargs['subcategories']
        if not isinstance(subcategories, list):
            return False, "'subcategories' must be a list"

        for subcategory in subcategories:
             
            if not isinstance(subcategory, dict) or 'number' not in subcategory or 'sub_category' not in subcategory or 'skippable' not in subcategory:
                return False, "Each subcategory in 'subcategories' must be a dictionary with 'number' and 'sub_category'and 'skippable' keys"

            if not isinstance(subcategory['skippable'], bool):
                return False, "'skippable' must be a boolean"

            if not isinstance(subcategory['number'], int):
                return False, "'number' in each subcategory must be an integer"

        return True,""



    def validate_additional_details(self, additional_details):            
        # Strip whitespace from both the required keys and the additional_details keys
        cleaned_additional_details = {k.strip(): v for k, v in additional_details.items()}
        cleaned_required_keys = [k.strip() for k in self.required_keys]

        for key in cleaned_required_keys:
            if key not in cleaned_additional_details:
                return False, f"Missing required key in additional details: {key}"

        # Validate role
        role = additional_details.get('role')
        if role and role not in self.valid_roles:
            return False, f"Invalid role: {role}. Valid options are: {self.valid_roles}"

        # Validate difficulty level
        difficulty_level = additional_details.get('difficulty_level')
        if difficulty_level and difficulty_level not in self.valid_difficulty_levels:
            return False, f"Invalid difficulty level: {difficulty_level}. Valid options are: {self.valid_difficulty_levels}"

        return True, ""

    def generate_assessment_attempt(self,user=None):
        is_valid, message = self.validate_additional_details(self.assessment_generation_details)
        if not is_valid:
            raise ValueError(message)
        
        is_valid, message = self.validate_kwargs()
        if not is_valid:
            raise ValueError(message)
        
        category = self.kwargs.get('category')
        subcategories = self.kwargs.get('subcategories')
        total_number = self.kwargs.get('total_number')
        question_data = AssessmentUseCase.fetch_question_ids_from_sub_category(category, total_number, subcategories)
        return question_data


class QuestionIdsBasedAssessment(BaseAssessmentGenerationLogic):
    def __init__(self, assessment_generation_id):
        super().__init__(assessment_generation_id)

    def validate_kwargs(self):
        required_keys = ['category', 'total_number', 'subcategories']
        for key in required_keys:
            if key not in self.kwargs:
                return False, f"Missing required key: {key}"

        if not isinstance(self.kwargs['total_number'], int):
            return False, "'total_number' must be an integer"

        subcategories = self.kwargs['subcategories']
        if not isinstance(subcategories, list):
            return False, "'subcategories' must be a list"

        for subcategory in subcategories:
            if not isinstance(subcategory, dict) or 'number' not in subcategory or 'question_ids' not in subcategory or 'skippable' not in subcategory or 'section_name' not in subcategory:
                return False, "Each subcategory must be a dictionary with 'number', 'question_ids', 'section_name', and 'skippable' keys"

            if not isinstance(subcategory['question_ids'], list):
                return False, "'question_ids' must be a list"

            if not all(isinstance(qid, int) for qid in subcategory['question_ids']):
                return False, "All question IDs must be integers"

            if not isinstance(subcategory['skippable'], bool):
                return False, "'skippable' must be a boolean"

            if not isinstance(subcategory['number'], int):
                return False, "'number' in each subcategory must be an integer"

        return True, ""

    def generate_assessment_attempt(self, user=None):
        is_valid, message = self.validate_kwargs()
        if not is_valid:
            raise ValueError(message)

        # Format the question data to match the expected format
        formatted_questions = []
        for subcategory in self.kwargs['subcategories']:
            formatted_questions.append({
                'section': subcategory['section_name'],
                'questions': subcategory['question_ids'],
                'skippable': subcategory['skippable']
            })

        return {
            'total_number': self.kwargs['total_number'],
            'category': self.kwargs['category'],
            'questions': formatted_questions
        }
    

class QuestionPoolBasedAssessment(BaseAssessmentGenerationLogic):
    def __init__(self, assessment_generation_id):
        super().__init__(assessment_generation_id)

    def validate_kwargs(self):
        required_keys = ['category', 'total_number', 'subcategories']
        for key in required_keys:
            if key not in self.kwargs:
                return False, f"Missing required key: {key}"

        if not isinstance(self.kwargs['total_number'], int):
            return False, "'total_number' must be an integer"

        subcategories = self.kwargs['subcategories']
        if not isinstance(subcategories, list):
            return False, "'subcategories' must be a list"

        for subcategory in subcategories:
            if not isinstance(subcategory, dict) or 'number' not in subcategory or 'question_pool' not in subcategory or 'skippable' not in subcategory or 'section_name' not in subcategory:
                return False, "Each subcategory must be a dictionary with 'number', 'question_pool', 'section_name', and 'skippable' keys"

            if not isinstance(subcategory['question_pool'], list):
                return False, "'question_pool' must be a list"

            if not all(isinstance(qid, int) for qid in subcategory['question_pool']):
                return False, "All question IDs in pool must be integers"

            if not isinstance(subcategory['skippable'], bool):
                return False, "'skippable' must be a boolean"

            if not isinstance(subcategory['number'], int):
                return False, "'number' in each subcategory must be an integer"

            if subcategory['number'] > len(subcategory['question_pool']):
                return False, f"Requested number of questions ({subcategory['number']}) is greater than the pool size ({len(subcategory['question_pool'])})"

        return True, ""

    def generate_assessment_attempt(self, user=None):
        import random

        is_valid, message = self.validate_kwargs()
        if not is_valid:
            raise ValueError(message)

        formatted_questions = []
        for subcategory in self.kwargs['subcategories']:
            # Randomly select the specified number of questions from the pool
            selected_questions = random.sample(
                subcategory['question_pool'], 
                subcategory['number']
            )
            
            formatted_questions.append({
                'section': subcategory['section_name'],
                'questions': selected_questions,
                'skippable': subcategory['skippable']
            })

        return {
            'total_number': self.kwargs['total_number'],
            'category': self.kwargs['category'],
            'questions': formatted_questions
        }
