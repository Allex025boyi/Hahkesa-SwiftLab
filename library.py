import os
import sys
from flask import (Flask, session, flash, Response, render_template, redirect, url_for,
                   request, Blueprint, send_from_directory, send_file)
from helper_functions import Get_DbConnection, normalized_subject, SUBJECT_IMOJIS, clean_filename
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import mysql.connector
from urllib.parse import quote
import cloudinary
import requests
from io import BytesIO
from cloudinary import exceptions
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract

load_dotenv()
library_bp = Blueprint('library_bp', __name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# ----------------------Library dashboard helper functions--------------------
def dashboardhelperfunction():
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            print("Failed to get database connection")
            return None
            
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""SELECT 
                        (SELECT COUNT(case when IS_PAPER=0 then 1 END) FROM books) AS TOTAL_BOOKS,
                        (SELECT COUNT(case when IS_PAPER=1 then 1 END) FROM books) AS TOTAL_EXAMPAPERS,
                        (SELECT COUNT(*) FROM books WHERE UPLOAD_DATE >=CURRENT_DATE()-INTERVAL 1 MONTH AND IS_PAPER=0) AS NEW_BOOKS,
                        (SELECT COUNT(*) FROM books WHERE UPLOAD_DATE>=CURRENT_DATE() -INTERVAL 1 MONTH AND IS_PAPER=1) AS NEW_PAPERS,
                        (SELECT SUM(DOWNLOAD_COUNT) FROM books WHERE IS_PAPER=0) AS TOTAL_BOOK_DOWNLOADS,
                        (SELECT SUM(DOWNLOAD_COUNT) FROM books WHERE IS_PAPER=1) AS TOTAL_PAPER_DOWNLOADS,
                        (SELECT SUM(VIEW_COUNT) FROM books WHERE IS_PAPER=0) AS VIEW_BOOK_TOTAL,
                        (SELECT SUM(VIEW_COUNT) FROM books WHERE IS_PAPER=1) AS VIEW_PAPER_TOTAL
                        FROM DUAL"""
                       )
        totaluploads = cursor.fetchone()
        return totaluploads
    except mysql.connector.Error as err:
        print(f"Error : {err}")
        return None
    except Exception as e:
        print(f"Error : {e}")
        return None
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# --------get books from the database by subject and level
def get_book_by_subject_and_level(level, subject):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        sql = """SELECT BOOK_ID,TITLE,AUTHOR,DESCRIPTION,FILE_SIZE,FORMAT,BOOK_YEAR,YEAR(UPLOAD_DATE) AS UYEAR
                FROM books WHERE SUBJECT=%s AND LEVEL=%s AND IS_PAPER=0 ORDER BY UPLOAD_DATE DESC
            """
        cursor.execute(sql, (subject, level))
        books = cursor.fetchall()
        return books
    except Exception as err:
        print(f"Error occured: {err}")
        return []
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# -----------get papers from database by subject and level
def get_papers_by_subject_and_level(level, subject):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        sql = """SELECT BOOK_ID,TITLE,AUTHOR,DESCRIPTION,FILE_SIZE,BOOK_YEAR,EXAMINATION_SEASON,FORMAT,YEAR(UPLOAD_DATE) AS UYEAR,
                coalesce(VIEW_COUNT,0) AS VIEWS,COALESCE(DOWNLOAD_COUNT,0) AS DOWNLOADS
                FROM books WHERE SUBJECT=%s AND LEVEL=%s AND IS_PAPER=1 ORDER BY UPLOAD_DATE DESC
            """
        cursor.execute(sql, (subject, level))
        papers = cursor.fetchall()
        return papers
    except Exception as err:
        print(f"Error occured: {err}")
        return []
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# --------Get books by id-------
def get_book_by_book_id(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE BOOK_ID=%s AND IS_PAPER=0", (book_id,))
        book = cursor.fetchone()
        return book
    except Exception as err:
        print(f"Error occured: {err}")
        return None
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# ---------get paper by id ------
def get_paper_by_id(paper_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE BOOK_ID=%s AND IS_PAPER=1", (paper_id,))
        paper = cursor.fetchone()
        return paper
    except Exception as err:
        print(f"Error occured: {err}")
        return None
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# -----------------increment book Views helper fuction ----------
def increment_book_views(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            print("Failed to get connection for incrementing book views")
            return False
            
        cursor = connection.cursor()
        cursor.execute("UPDATE books SET VIEW_COUNT=COALESCE(VIEW_COUNT,0)+1 WHERE BOOK_ID=%s AND IS_PAPER=0", (book_id,))
        connection.commit()
        return True
    except Exception as err:
        print(f"Error occured: {err}")
        if connection and connection.is_connected():
            try:
                connection.rollback()
            except:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# --------------increment paper views helper function-------------
def increment_paper_views(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            print("Failed to get connection for incrementing paper views")
            return False
            
        cursor = connection.cursor()
        cursor.execute("UPDATE books SET VIEW_COUNT=COALESCE(VIEW_COUNT,0)+1 WHERE BOOK_ID=%s AND IS_PAPER=1", (book_id,))
        connection.commit()
        return True
    except Exception as err:
        print(f"Error Occured: {err}")
        if connection and connection.is_connected():
            try:
                connection.rollback()
            except:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# ------------increment book download counthelper functions-----------
def increment_book_downloads(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            print("Failed to get connection for incrementing book downloads")
            return False
            
        cursor = connection.cursor()
        cursor.execute("UPDATE books SET DOWNLOAD_COUNT=COALESCE(DOWNLOAD_COUNT,0)+1 WHERE BOOK_ID=%s AND IS_PAPER=0", (book_id,))
        connection.commit()
        return True
    except Exception as err:
        print(f"Error occured: {err}")
        if connection and connection.is_connected():
            try:
                connection.rollback()
            except:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# -----------increment paper download count helper function -----------
def increment_paper_downloads(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            print("Failed to get connection for incrementing paper downloads")
            return False
            
        cursor = connection.cursor()
        cursor.execute("UPDATE books SET DOWNLOAD_COUNT=COALESCE(DOWNLOAD_COUNT,0)+1 WHERE BOOK_ID=%s AND IS_PAPER=1", (book_id,))
        connection.commit()
        return True
    except Exception as err:
        print(f"Error occured: {err}")
        if connection and connection.is_connected():
            try:
                connection.rollback()
            except:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# --------get book count by level and subject ---------
def get_book_count():
    connection = None
    cursor = None
    bookcounts = {}
    try:
        connection = Get_DbConnection()
        if not connection:
            return {}
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT LEVEL,SUBJECT,COUNT(*) AS TOTAL FROM books WHERE IS_PAPER=0 group by LEVEL, SUBJECT")
        result = cursor.fetchall()
        for row in result:
            key = f"{row['LEVEL']}_{row['SUBJECT']}"
            bookcounts[key] = row["TOTAL"]
        return bookcounts
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# ----------get papers count per each subject
def get_paper_count():
    connection = None
    cursor = None
    paper_counts = {}
    try:
        connection = Get_DbConnection()
        if not connection:
            return {}
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT LEVEL, SUBJECT, COUNT(*) as TOTAL FROM books where IS_PAPER=1 group by LEVEL, SUBJECT")
        results = cursor.fetchall()
        for row in results:
            key = f"{row['LEVEL']}_{row['SUBJECT']}"
            paper_counts[key] = row['TOTAL']
        return paper_counts
    except mysql.connector.Error as err:
        print(f"Database error occured: {err}")
        return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# ------------------Delete book by Book_id------------
def delete_book_by_book_id(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        cursor.execute("DELETE FROM books WHERE BOOK_ID=%s AND IS_PAPER=0", (book_id,))
        connection.commit()
        return True
    except Exception as err:
        print(f"Error occured: {err}")
        if connection and connection.is_connected():
            try:
                connection.rollback()
            except:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass

# -------------------delete paper using book_id
def delete_paper_by_book_id(book_id):
    connection = None
    cursor = None
    try:
        connection = Get_DbConnection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        cursor.execute("DELETE FROM books WHERE BOOK_ID =%s AND IS_PAPER=1", (book_id,))
        connection.commit()
        return True
    except Exception as err:
        print(f"Error occured: {err}")
        if connection and connection.is_connected():
            try:
                connection.rollback()
            except:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass


@library_bp.route("/")
def library_dashboard():
    book_counts = get_book_count()
    paper_counts = get_paper_count()
    totaluploads = dashboardhelperfunction()
    return render_template('library.html', totaluploads=totaluploads, SUBJECT_IMOJIS=SUBJECT_IMOJIS, book_counts=book_counts, paper_counts=paper_counts)


# route for uploading a new file
@library_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        connection = None
        cursor = None
        
        subject = request.form.get('subject')
        level = request.form.get('level')
        language = request.form.get('language')
        category = request.form.get('category')
        book_upload = request.files.get('Upload')
        is_paper = 1 if request.form.get('uploadType') == 'paper' else 0
        cleaned_name = clean_filename(book_upload.filename)
        secured_bookname = secure_filename(cleaned_name)
        year = None
        exam_season = None
        
        if is_paper == 1:
            year = request.form.get('year')
            author = request.form.get('exambody')
            exam_season = request.form.get('examseason')
            description = f"This is a {subject} question paper for the {author} {level} level {exam_season} {year} session "
        else:
            author = request.form.get('author')
            description = f"{secured_bookname} is an {level} {subject} book written by {author if author.strip() else 'Unkown Author'} "
        
        file_type = book_upload.filename.rsplit(".", 1)[1].upper() if "." in book_upload.filename else "PDF"
        
        # Upload to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                book_upload,
                folder="library_books",
                resource_type="auto",
                public_id=secured_bookname.rsplit(".", 1)[0],
                overwrite=False,
                unique_filename=True,
                tags=[category, level, language]
            )
            
            cloudinary_url = upload_result['secure_url']
            public_id = upload_result['public_id']
            book_size = round(upload_result['bytes'] / (1024 * 1024), 2)
            print(f"The uploaded book public id is {public_id}")
           
        except cloudinary.exceptions.Error as cloud_err:
            print(f"Cloudinary error: {cloud_err}")
            flash(f"File upload error: {cloud_err}", "error")
            return redirect(url_for('library_bp.library_dashboard'))
        
        # Database insert
        try:
            connection = Get_DbConnection()
            if not connection:
                flash("Database connection failed. Please try again.", "error")
                return redirect(url_for('library_bp.library_dashboard'))
            
            cursor = connection.cursor()
            sql = """INSERT INTO books (TITLE,AUTHOR,DESCRIPTION ,SUBJECT,CATEGORY,
                LEVEL,FORMAT,CLOUDINARY_PUBLIC_ID,LANGUAGE,FILENAME,FILE_PATH,FILE_SIZE,BOOK_YEAR,
                UPLOAD_DATE,IS_PAPER,EXAMINATION_SEASON) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s) """
            
            values = (secured_bookname, author, description, normalized_subject(subject), category, level,
                     file_type, public_id, language, secured_bookname, cloudinary_url, book_size, year, is_paper, exam_season)
            
            cursor.execute(sql, values)
            connection.commit()
            
            print(f"Book succesfully added {values}")
            flash(f"{'Paper' if is_paper == 1 else 'Book'} {secured_bookname} uploaded successfully", "success")
            return redirect(url_for('library_bp.library_dashboard'))
            
        except Exception as err:
            print(f"error DATABASE {err}")
            flash(f"Database error: {err}", "error")
            if connection and connection.is_connected():
                try:
                    connection.rollback()
                except Exception as rollback_err:
                    print(f"Rollback Error: {rollback_err}")
            return redirect(url_for('library_bp.library_dashboard'))
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection and connection.is_connected():
                try:
                    connection.close()
                except:
                    pass


# viewing the pdf file
@library_bp.route("/view_pdf/<int:book_id>", methods=["GET"])
def view_pdf(book_id):
    connection = None
    cursor = None
    level = None
    subject = None
    is_paper = False
    cloudinary_url = None
    
    try:
        connection = Get_DbConnection()
        if not connection:
            print("Failed to get database connection")
            flash("Database connection failed", "error")
            return redirect(url_for('library_bp.library_dashboard'))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE BOOK_ID=%s", (book_id,))
        result = cursor.fetchone()
        
        if not result:
            flash("File not found", "error")
            return redirect(url_for('library_bp.library_dashboard'))
        
        level = result.get('LEVEL')
        subject = result.get('SUBJECT')
        is_paper = result.get('IS_PAPER') == 1
        cloudinary_url = result.get('FILE_PATH')
        
        if not cloudinary_url:
            flash("File path not found", "error")
            if is_paper:
                return redirect(url_for('library_bp.view_papers', level=level, subject=subject))
            else:
                return redirect(url_for('library_bp.view_books', level=level, subject=subject))
        
        # Increment views
        if is_paper:
            print(f"Opening cloudinary link: {cloudinary_url}")
            if increment_paper_views(book_id):
                print("Paper view incremented by 1")
            else:
                print("Paper view increment failed")
        else:
            print(f"Opening cloudinary link: {cloudinary_url}")
            if increment_book_views(book_id):
                print("Book view incremented by 1")
            else:
                print("Book view increment failed")
        
        return redirect(cloudinary_url)
        
    except mysql.connector.Error as err:
        print(f"Error from Database: {err}")
        flash("Database error occurred", "error")
        if is_paper and level and subject:
            return redirect(url_for('library_bp.view_papers', level=level, subject=subject))
        elif level and subject:
            return redirect(url_for('library_bp.view_books', level=level, subject=subject))
        else:
            return redirect(url_for('library_bp.library_dashboard'))
            
    except Exception as e:
        print(f"Error: {e}")
        flash("An error occurred", "error")
        if is_paper and level and subject:
            return redirect(url_for('library_bp.view_papers', level=level, subject=subject))
        elif level and subject:
            return redirect(url_for('library_bp.view_books', level=level, subject=subject))
        else:
            return redirect(url_for('library_bp.library_dashboard'))
            
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection and connection.is_connected():
            try:
                connection.close()
            except:
                pass


# ----------------view books route -----------------------
@library_bp.route("/books/<level>/<subject>")
def view_books(level, subject):
    category = request.args.get('catagory', 'none')
    print(f"THE USER {subject}")
    books = get_book_by_subject_and_level(level, subject)
    return render_template("booklist.html", category=category, subject=subject, level=level, books=books, is_papers=False)


# ----------------view papers route -----------------------
@library_bp.route("/papers/<level>/<subject>")
def view_papers(level, subject):
    category = request.args.get('catagory', 'none')
    papers = get_papers_by_subject_and_level(level, subject)
    print(f"THE USER {subject}")
    return render_template("booklist.html", category=category, subject=subject, level=level, books=papers, is_papers=True)


# ------------------route for download-----------
@library_bp.route("/book/<int:book_id>/download")
def download_pdf(book_id):
    custom_name = None
    level = None
    subject = None
    book = get_book_by_book_id(book_id)
    
    if book is not None and book.get('FILE_PATH'):
        url = book['FILE_PATH']
        level = book.get('LEVEL')
        subject = book.get('SUBJECT')
        if 'cloudinary.com' in url:
            custom_name = book.get('FILENAME', 'document.pdf')
            try:
                print(f"The URL is: {url}")
                print(f"The level is: {level}")
                print(f"The Custom name is: {custom_name}")
                print(f"The subject is: {subject}")
                response = requests.get(url)
                response.raise_for_status()
                increment_book_downloads(book_id)
                return send_file(BytesIO(response.content), mimetype='application/pdf',
                               as_attachment=True, download_name=custom_name)
            except Exception as e:
                print(f"ERROR OCCURED: {e}")
                flash(f"Download failed please try again later!", "error")
                return redirect(url_for('library_bp.view_books', level=level, subject=subject))
    
    # -----------downloading paper
    paper = get_paper_by_id(book_id)
    if paper is not None and paper.get('FILE_PATH'):
        url = paper.get('FILE_PATH')
        level = paper.get('LEVEL')
        subject = paper.get('SUBJECT')
        if 'cloudinary.com' in url:
            custom_name = paper.get('FILENAME')
            try:
                print(f"The URL is: {url}")
                print(f"The level is: {level}")
                print(f"The subject is: {subject}")
                print(f"The Custom name is: {custom_name}")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                increment_paper_downloads(book_id)
                return send_file(BytesIO(response.content), mimetype='application/pdf',
                               as_attachment=True, download_name=custom_name)
            except Exception as e:
                print(f"ERROR OCCURED: {e}")
                flash(f"Download failed please try again later!", "error")
                return redirect(url_for('library_bp.view_papers', level=level, subject=subject))
    
    # If we get here, neither book nor paper was found
    flash("File not found", "error")
    return redirect(url_for('library_bp.library_dashboard'))


# -------------------------share app route -----------------
@library_bp.route("/book/share/<level>/<subject>")
def share(level, subject):
    if subject.lower() in SUBJECT_IMOJIS:
        subject_imoji = SUBJECT_IMOJIS.get(subject.lower(), '📚')
    link = url_for('library_bp.view_books', level=level, subject=subject, _external=True)
    raw_message = (f"{subject_imoji}*Check out these {subject.title()} books on our site!*{subject_imoji}\n\n "
                  f"Subject: {subject.title()}\n"
                  f"Level: {level.title()} Level\n\n"
                  f"👇 Click the link below to view:\n"
                  f"{link}"
                  )
    encoded_message = quote(raw_message)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"
    print(f"THE BOOK LINK IS {link}")
    print(f"WHATSAPP LINK {whatsapp_url}")
    return redirect(whatsapp_url)


# --------------------Delete both books and papers route----------------
@library_bp.route("/book/<int:book_id>/delete", methods=["GET", "POST"])
def delete_books_and_papers(book_id):
    level = None
    subject = None
    is_paper = False
    
    try:
        # Try to get as book first
        item = get_book_by_book_id(book_id)
        
        if item is None:
            # If not a book, try as paper
            item = get_paper_by_id(book_id)
            is_paper = True
        
        if item is None:
            flash("File not found", "error")
            return redirect(url_for('library_bp.library_dashboard'))
        
        level = item.get('LEVEL')
        subject = item.get('SUBJECT')
        public_id = item.get('CLOUDINARY_PUBLIC_ID')
        
        if not public_id:
            flash("File has no saved public ID", "error")
            print(f"File has no saved public id")
        else:
            try:
                # Delete from Cloudinary
                result = cloudinary.uploader.destroy(public_id, resource_type="image")
                if result.get('result') == "ok":
                    flash("File has been deleted successfully from Cloudinary", "success")
                    print(f"File deleted successfully from cloudinary: {public_id}")
                else:
                    flash("File deletion from Cloudinary failed", "error")
                    print(f"File failed to be deleted from cloudinary: {result}")
            except Exception as e:
                print(f"Cloudinary deletion error: {e}")
                flash(f"Cloudinary error: {e}", "error")
        
        # Delete from database
        if is_paper:
            DB_delete = delete_paper_by_book_id(book_id)
        else:
            DB_delete = delete_book_by_book_id(book_id)
        
        if DB_delete:
            flash("File has been deleted successfully from the database", "success")
            print(f"Deletion from database successful")
        else:
            flash("File deletion from database failed", "error")
            print(f"Deletion from database failed")
        
        # Redirect to appropriate page
        if is_paper:
            return redirect(url_for('library_bp.view_papers', level=level, subject=subject))
        else:
            return redirect(url_for('library_bp.view_books', level=level, subject=subject))
            
    except Exception as err:
        print(f"Error occurred: {err}")
        flash(f"An error occurred: {err}", "error")
        if level and subject:
            if is_paper:
                return redirect(url_for('library_bp.view_papers', level=level, subject=subject))
            else:
                return redirect(url_for('library_bp.view_books', level=level, subject=subject))
        return redirect(url_for('library_bp.library_dashboard'))


