# program to fine tune camembert with gallica newspapers sample of sentences.

#  few-sample fine tuning best practice :
# https://towardsdatascience.com/advanced-techniques-for-fine-tuning-transformers-82e4e61e16e
# REVISITING FEW-SAMPLE BERT FINE-TUNING - ICLR 2021 - https://arxiv.org/pdf/2006.05987.pdf


# references
# https://huggingface.co/transformers/v4.10.1/custom_datasets.html
# https://huggingface.co/docs/transformers/master/en/training#finetuning-a-pretrained-model
# (notebook) https://colab.research.google.com/github/huggingface/notebooks/blob/master/transformers_doc/training.ipynb#scrollTo=1HEBx0__pWtp

from datasets import load_dataset,load_metric, list_datasets, list_metrics, DatasetDict
import transformers
print(transformers.__version__)
from transformers import AutoTokenizer, AutoModelForMaskedLM
from transformers import Trainer, TrainingArguments
import math, os
from glob import glob
import numpy as np
os.environ["WANDB_DISABLED"] = "true"

# load datasets
# https://github.com/huggingface/datasets
# https://huggingface.co/docs/datasets/loading_datasets.html#from-local-files
# https://huggingface.co/docs/datasets/loading.html
#datasets = load_dataset("wikitext", "wikitext-2-raw-v1")
# datasets = load_dataset("text", data_files={"train": path_to_train.txt, "validation": path_to_validation.txt}
#print(datasets)
#print(datasets['train'].info)
#print(datasets['train'].features)
#print(datasets['train'].shape)
#print(datasets['train'][0])
#print(list_datasets())
#print(list_metrics())
#print(datasets['train'][0:2])

# datatset from local files
files = glob("./input_files/gallica.acception.csv")
dataset_tmp = load_dataset('csv', data_files=files)
dataset_tmp = dataset_tmp.remove_columns(['year', 'key_word'])
#dataset_tmp = dataset_tmp.rename_column(['sentence', 'text'])
train_test_ds = dataset_tmp['train'].train_test_split(test_size=0.1)
print(train_test_ds)


exit()

## language modeling (mask task)
#model_checkpoint = 'distilroberta-base' 
model_checkpoint = 'camembert-base' 
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, use_fast=True)

# tokenize dataset text
#inputs = tokenizer(sentences, padding="max_length", truncation=True)
def tokenize_function(examples):
    return tokenizer(examples["sentence"], padding="max_length", max_length=20, truncation=True)

tokenized_train_ds = train_test_ds['train'].map(tokenize_function, batched=True)
#tokenized_test_ds = train_test_ds['test'].map(tokenize_function, batched=True)
tokenized_eval_ds = train_test_ds['valid'].map(tokenize_function, batched=True)
# sampling
#small_train_dataset = tokenized_train_ds.shuffle(seed=42).select(range(5000)) 
#small_eval_dataset = tokenized_eval_ds.shuffle(seed=42).select(range(1000)) 

# loading automodelfor mask modeling as a base
model = AutoModelForMaskedLM.from_pretrained(model_checkpoint)

model_name = model_checkpoint.split("/")[-1]

## training arguments and class definition
# https://huggingface.co/docs/transformers/master/en/main_classes/trainer#transformers.TrainingArguments
training_args = TrainingArguments(
    #f"{model_name}-finetuned-gallica",
    output_dir='./results',
    evaluation_strategy = "epoch",
    #learning_rate=2e-5,
    #weight_decay=0.01,
    #push_to_hub=False,
)

# metric used
metric = load_metric("accuracy")
#print(metric.inputs_description)
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)


# specific to Mask model : we need to randomly mask words 
from transformers import DataCollatorForLanguageModeling
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm_probability=0.15)

# trainer definition
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train_ds,#mall_train_dataset,
    eval_dataset=tokenized_eval_ds,#small_eval_dataset,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)
trainer.train()

# pushing to model hub
#You can now share this model with all your friends, family, favorite pets: they can all load it with the identifier "your-username/the-name-you-picked" so for instance:
#trainer.push_to_hub()