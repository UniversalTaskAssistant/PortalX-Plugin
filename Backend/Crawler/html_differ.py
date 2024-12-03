from bs4 import BeautifulSoup
import graphtage
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def html_to_dict(html):
    soup = BeautifulSoup(html, 'html.parser')

    def recursive_dict(element):
        if isinstance(element, str):
            return element.strip()

        result = {}

        for child in element.children:
            if isinstance(child, str):
                continue
            tag_name = child.name
            child_dict = recursive_dict(child)
            
            if tag_name in result:
                if isinstance(result[tag_name], list):
                    result[tag_name].append(child_dict)
                else:
                    result[tag_name] = [result[tag_name], child_dict]
            else:
                result[tag_name] = child_dict
        
        if element.string and element.string.strip():
            if element.name in result:
                result[element.name] = [result[element.name], element.string.strip()]
            else:
                result[element.name] = element.string.strip()

        return result
    
    html_dict = recursive_dict(soup)
    logging.info(json.dumps(html_dict, indent=4))

    return html_dict

def diff_html(new_html, template_html):
    new_dict = html_to_dict(new_html)
    template_dict = html_to_dict(template_html)

    new_tree = graphtage.json.build_tree(new_dict)
    template_tree = graphtage.json.build_tree(template_dict)
    
    diff = new_tree.diff(template_tree)
    with graphtage.printer.DEFAULT_PRINTER as p:
        logging.info(f'Diff status:')
        graphtage.json.JSONFormatter.DEFAULT_INSTANCE.print(graphtage.printer.DEFAULT_PRINTER, diff)

    edits = list(new_tree.get_all_edits(template_tree))
    logging.info(f'All diffing edits: {edits}')
    
    # TODO: When we save new templates...
    # if xxx:
    #     logging.info('No differences found, saving the new HTML as a new template.')
    #     save_template(new_html)
    #     return None
    
    # TODO: When we delete the identical parts...
    # new_soup = BeautifulSoup(new_html, 'html.parser')
    # for xxx:
    #     logging.info(f'Processing edit: {edit}')
    #     if xxx:
    #         process_removal(edit, new_soup)
    # logging.info(f'New HTML after editting: {new_soup}')

def save_template(template_html, file_path='new_template.html'):
    with open(file_path, 'w') as f:
        f.write(template_html)
    logging.info(f'Template saved to {file_path}')


if __name__ == '__main__':
    # Example usage
    new_html = '''
    <html>
    <body>
        <h1>Welcome to My Website</h1>
        <p>This is a new page</p>    
    </body>
    </html>
    '''

    template_html = '''
    <html>
    <body>
        <h1>Welcome to My Website</h1>
        <p>This is a test page</p>
        <div>div</div>
    </body>
    </html>
    '''

    diff_html(new_html, template_html)
