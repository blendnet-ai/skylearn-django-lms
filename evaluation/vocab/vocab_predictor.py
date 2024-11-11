import os
os.environ["REPLICATE_API_TOKEN"]="r8_43de5PXPa3lUzZG0r9tnbhXF62qCcha2iruta"
import replicate
import datetime
import json
import logging
logger = logging.getLogger(__name__)

def evaluate_vocab_level(user_answer):
    current_datetime = datetime.datetime.now()
    output = replicate.run(
        "sanchitsharma/cefr-predictor:be59782d8ae9386f84183f40d8813b40e29b6143529fef1ddd3fe216c89b4571",
        input={
            "text":user_answer,
        }
    )
    logger.info("Time taken for cefr - {}".format((datetime.datetime.now()-current_datetime).total_seconds()))
    logger.info("Overall levels - {}".format(output))
    logger.info(f"Vocab level evaluated - {output[0]['level']}")
    if "+" in output[0]["level"]:
        return output[0]["level"].replace("+", "")
    return output[0]["level"]
