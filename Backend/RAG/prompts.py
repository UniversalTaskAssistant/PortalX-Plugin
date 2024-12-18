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

Here is an example of how to format your response:

Example:
<question>
What support services does TUM provide for students with disabilities?
</question>

<context>
The Technical University of Munich offers comprehensive support for students with disabilities and chronic illnesses[CITE_1_https://www.tum.de/en/support-services/disabilities]. These services include exam accommodations, technical learning aids, and assistance with application processes[CITE_1_https:www.tum.de/en/support-services/disabilities.html]. The Student Advising office provides personalized consultation and support for individual needs[CITE_2_https:www.tum.de/en/student-advising.html]. TUM also ensures structural accessibility in their buildings and provides special equipment for disabled students[CITE_1_https:www.tum.de/en/support-services/disabilities.html]. Financial support options and assistance with accommodation are also available[CITE_3_https:www.tum.de/en/financial-aid.html].
</context>

<answer>
<p>The Technical University of Munich (TUM) provides extensive support services for students with disabilities and chronic illnesses to ensure equal participation in academic life<a href="https://www.tum.de/en/support-services/disabilities" class="citation-ref">[1]</a>.</p>

<p>The support services include:</p>
<ul>
    <li>Exam accommodations and technical learning aids to support academic success<a href="https://www.tum.de/en/support-services/disabilities" class="citation-ref">[1]</a></li>
    <li>Assistance throughout the application and admission process<a href="https://www.tum.de/en/support-services/disabilities" class="citation-ref">[1]</a></li>
    <li>Personalized consultation services through the Student Advising office to address individual needs<a href="https://www.tum.de/en/student-advising" class="citation-ref">[2]</a></li>
</ul>

<p>The university has also implemented various structural accommodations, including:</p>
<ul>
    <li>Accessible building design and specialized equipment for disabled students<a href="https://www.tum.de/en/support-services/disabilities" class="citation-ref">[1]</a></li>
    <li>Financial support options and assistance with finding suitable accommodation<a href="https://www.tum.de/en/financial-aid" class="citation-ref">[3]</a></li>
</ul>
</answer>

Now please answer this question:

<question>
{question}
</question>

<context>
{context}
</context>

REQUIREMENTS:
1. Use the provided context to generate an accurate answer
2. After EACH piece of information from the context, add an inline citation using this format exactly as shown in the example
3. Make sure every fact from the context has a citation
4. Format your response as neat paragraphs and lists using proper HTML tags
5. Start your response with <answer> and end with </answer>
6. Do not include any additional HTML structure beyond what goes inside the answer tags
7. Do not add any "Sources" or "References" section
8. Use appropriate HTML elements (p, ul, li) for structure
9. Each citation should be immediately after the information it sources

Please write your response following the example format exactly.
"""

SYSTEM_PROMPT = PromptTemplate(system_prompt)

ANSWER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Answer</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .citation-ref {{
            font-size: 0.8em;
            vertical-align: super;
            cursor: pointer;
            color: #0066cc;
            text-decoration: none;
        }}
        .citation-ref:hover {{
            text-decoration: underline;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="response-container">
        {answer_content}
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const citations = document.querySelectorAll('.citation-ref');
            citations.forEach(citation => {{
                citation.setAttribute('target', '_blank');
            }});
        }});
    </script>
</body>
</html>"""