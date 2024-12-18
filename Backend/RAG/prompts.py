from llama_index.core.prompts import PromptTemplate

compress_and_filter_prompt = f"""
The following is a document retrieved based on a user question:\n\n
Question: {{query}}\n\n
Document Text:{{text}}\n\n
"Task:\n"
    1. Analyze the document and extract only the text segments that directly answer the question or are essential to understanding the answer.\n"
       a. Remove any unrelated or tangential content.\n"
       b. Ensure the retained text segments are verbatim excerpts from the document, without paraphrasing or summarizing.\n"
    2. Identify and list any URLs explicitly relevant to the user's query, providing their purpose.\n"
       a. Exclude URLs that do not directly contribute to answering the question.\n"
    3. Extract any contact information mentioned in the document that is directly tied to the question, specifying whom the contact information pertains to.\n"
       a. Exclude unrelated or tangential contact information.\n\n"
"Output:\n"
    "Relevant Text Excerpts:\n"
    "Relevant URLs and Purpose:\n"
    "Relevant Contact Information:"
"""

COMPRESS_AND_FILTER_PROMPT = PromptTemplate(compress_and_filter_prompt)



answer_prompt = f"""
<instructions>
You are an intelligent, friendly, and professional chatbot specialized in answering user questions based on information retrieved from websites. Below, you are provided with the user's question, and a context containing relevant information retrieved from the database.

<question>
{{question}}
<question>

<context>
{{context}}
</context>

Your task:
1. Generate a concise and accurate answer to the user's question based on the given context. 
2. If the answer is derived from the context, reference the specific source by its number in brackets '[x]'.
3. If you are unsure or the required information is not in the context, let the user know politely and suggest alternative actions, such as referring them to official contact details or relevant website links, if available in the context.
4. If the user's query contains ambiguous terms or unclear references, ask for clarification before generating a detailed response.
</instructions>

Answer:
"""

ANSWER_PROMPT = PromptTemplate(answer_prompt)

system_prompt = """You are a helpful AI website customer assistant that provides clear, structured answers based on website information.

<question>
{question}
</question>

<context>
{context}
</context>

<template>
{html_template}
</template>

REQUIREMENTS:
1. Generate accurate answers based on the given context
2. The context contains citation markers in HTML format - preserve these exactly as they appear
3. Structure your response to fit in the provided HTML template
4. Keep all HTML markup intact when using information from the context
5. Do not modify or remove any citation spans or numbers
6. Format your response as paragraphs and lists when appropriate, using proper HTML tags

Please provide your response in HTML format, using the template provided.
"""

SYSTEM_PROMPT = PromptTemplate(system_prompt)