from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import pandas as pd
import os

app = Flask(__name__)
load_dotenv('.env.local')

# Configure Google API key for Google Books API
google_api_key = os.getenv('GOOGLE_API_KEY')

# Configure GenAI API key
genai_api_key = os.getenv('GENAI_API_KEY')
genai.configure(api_key=genai_api_key)
model = genai.GenerativeModel('gemini-pro')

def fetch_book_details(isbn, google_api_key):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={google_api_key}"
    response = requests.get(url)
    data = response.json()
    
    if 'items' in data:
        for item in data['items']:
            volume_info = item.get('volumeInfo')
            if volume_info:
                title = volume_info.get('title', 'No Title')
                authors = volume_info.get('authors', ['Unknown Author'])
                image_links = volume_info.get('imageLinks', {})
                thumbnail = image_links.get('thumbnail', 'No Image')
                publisher = volume_info.get('publisher', 'No Publisher Found')
                pageCount = volume_info.get('pageCount', 'Page count not available')
                return title, authors, thumbnail, publisher, pageCount
    # If book details are not found, return None
    return None, None, None, None, None

def get_response(prompt, generation_config={}):
    response = model.generate_content(contents=prompt, generation_config=generation_config)
    return response

def save_to_excel(data):
    df = pd.DataFrame(data, columns=['Title', 'Authors', 'Publisher', 'Page Count'])
    df.to_excel('book_details.xlsx', index=False)

@app.route('/')
def index():
    return render_template('index.html')
# window.location.replace("/update/${editedTitle}/${editedAuthor}/${editedPublisher}/${editedPageCount}/${editedThumbnail}")

@app.get("/update/<string:editedTitle>/<string:editedAuthor>/<string:editedPublisher>/<int:editedPageCount>/<string:editedThumbnail>")
def Update(editedTitle,editedAuthor,editedPublisher,editedPageCount,editedThumbnail):
    data = [editedTitle,editedAuthor,editedPublisher,editedPageCount,editedThumbnail]
    if os.path.exists("update_book_details.xlsx"):
        df = pd.read_excel("update_book_details.xlsx")
        df.loc[len(df)-1] = data  
    else:
        print(data)
        df = pd.DataFrame([data], columns=['Title', 'Authors', 'Publisher', 'Page Count', 'Thumnbnail'])
    df.to_excel('book_details.xlsx', index=False, sheet_name="Updated")
    return redirect("/")


@app.route('/fetch_details', methods=['POST'])
def fetch_details():
    isbn = request.form.get('isbn')
    if isbn:
        title, authors, thumbnail, publisher, pageCount = fetch_book_details(isbn, google_api_key)
        categories = "Your categories"  
        ageGroup = "Your age group"    
        if title and authors:
            book_description = get_response(f"Book Description Prompt: Craft a compelling description for the book '{title}' by {' and '.join(authors)}, in exact 300 words. Highlight the key themes, plot points, and unique selling proposition, emphasizing what makes this book truly exceptional and captivating potential readers with its intrigue, depth, and relevance.").text
            author_description = get_response(f"Write an engaging biography for the {' and '.join(authors)} of the book '{title}', providing insight into their background, writing style, and notable achievements within 200 words. Capture the essence of the author's expertise, passion, and contribution to the literary world, showcasing why readers should be excited to explore their work.").text
            meta_description = get_response(f"Create a compelling meta description for the book '{title}' by {' and '.join(authors)} in 150-160 characters. Summarize the essence of the book, enticing potential readers with its intrigue and relevance. Incorporate relevant keywords and a captivating call-to-action to encourage clicks and engagement.").text

            bookDet = get_response(f"Provide details for the book {title} by {' and '.join(authors)} ISBN {isbn} in the HTML format, specific details are categories and age-group in number. Provide me these details in the aligned format, keep the headings like category and age-group in bold and the value in normal, and should have line space between both the data. Give me the HTML code.").text

            book_details = bookDet.strip().replace('```html\n', '').replace('\n```', '')

            return render_template('index.html', title=title, authors=authors, thumbnail=thumbnail, publisher=publisher, pageCount=pageCount, description=book_description, author_description=author_description, meta_description=meta_description, book_details=book_details, categories=categories, ageGroup=ageGroup)
        else:
            return render_template('index.html', error="Book details not found.")
    else:
        author = request.form.get('author')
        book = request.form.get('book')
        if book and author:
            # Generate descriptions
            manual_book_description = get_response(f"Book Description Prompt: Craft a compelling description for the book '{book}' by {author}, in exact 300 words. Highlight the key themes, plot points, and unique selling proposition, emphasizing what makes this book truly exceptional and captivating potential readers with its intrigue, depth, and relevance.").text
            manual_author_description = get_response(f"Write an engaging biography for {author} of the book '{book}', providing insight into their background, writing style, and notable achievements within 200 words. Capture the essence of the author's expertise, passion, and contribution to the literary world, showcasing why readers should be excited to explore their work.").text
            manual_meta_description = get_response(f"Create a compelling meta description for the book '{book}' by {author} in 150-160 characters. Summarize the essence of the book, enticing potential readers with its intrigue and relevance. Incorporate relevant keywords and a captivating call-to-action to encourage clicks and engagement.").text

            manual_bookDet = get_response(f"Provide details for the book {book} by {author} in the HTML format, specific details are categories and age-group in number. Provide me these details in the aligned format, keep the headings like category and age-group in bold and the value in normal, and should have line space between both the data. Give me the HTML code.").text

            book_details = manual_bookDet.strip().replace('```html\n', '').replace('\n```', '')

            return render_template('index.html', title=book, authors=author, description=manual_book_description, author_description=manual_author_description, meta_description=manual_meta_description, book_details=book_details)
        else:
            return render_template('index.html', error="Author and book name must be provided.")

@app.route('/save_to_excel', methods=['POST'])
def save_to_excel():
    # Retrieve data from the hidden input field
    excel_data = request.form.get('excelData')
    
    if not excel_data:
        return render_template('index.html', error_message="No data provided to save to Excel.")

    # Split the data into lines and create a dictionary
    data_lines = excel_data.split('\n')
    data_dict = {}
    for line in data_lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            data_dict[key] = value

    # Create a DataFrame with the collected data
    df = pd.DataFrame([data_dict])

    # Specify the path to the "Downloads" directory
    downloads_dir = os.path.expanduser("~/Downloads")  # Get the user's "Downloads" directory

    # Specify the full path to the Excel file in the "Downloads" directory
    excel_file_path = os.path.join(downloads_dir, 'book_details.xlsx')

    # Save the DataFrame to an Excel file
    try:
        df.to_excel(excel_file_path, index=False)
        return render_template('index.html', success_message="Data saved to Excel successfully!")
    except Exception as e:
        return render_template('index.html', error_message=f"An error occurred: {str(e)}")




if __name__ == '__main__':
    app.run(debug=True)