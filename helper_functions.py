import os
from flask import Flask 
import phonenumbers
import mysql.connector
from mysql.connector import pooling

from dotenv import load_dotenv
import re
from decimal import Decimal,InvalidOperation
load_dotenv()
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_PORT = int(os.getenv('DB_PORT',14747))
DATABASE_URL=os.getenv('DATABASE_URL')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_CA_PATH = os.path.join(BASE_DIR, 'ca.pem')

# For Render deployment (secret files are mounted here)
RENDER_CA_PATH = '/etc/secrets/ca.pem'

# Choose the right path
if os.path.exists(RENDER_CA_PATH):
    CA_PATH = RENDER_CA_PATH
    print(f"Using Render CA certificate: {CA_PATH}")
elif os.path.exists(LOCAL_CA_PATH):
    CA_PATH = LOCAL_CA_PATH
    print(f"Using local CA certificate: {CA_PATH}")
else:
    # Fallback: try environment variable
    CA_PATH = os.getenv('CA_CERT_PATH', LOCAL_CA_PATH)
    print(f"Using fallback CA certificate path: {CA_PATH}")


#Database configurations
db_config={
        "host":DB_HOST,
        "user":DB_USER,
        "password":DB_PASSWORD,
        "database":DB_DATABASE,
        "port":DB_PORT,
        "ssl_verify_cert": False,  # ⚠️ Less secure
        "ssl_disabled": False,
        "use_pure": True
}

#This pooling makes connections so user dont wait 5 minutes 
db_pool=mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",pool_size=20,**db_config)
#Establishing the database connection. Connection helper function
def Get_DbConnection ():
    return db_pool.get_connection()

#----------------------get book counts function------------------
# def get_book_counts():
#     connection=None
#     counts={}
#     try:
#         connection=Get_DbConnection()
#         cursor=connection.cursor(dictionary=True)
#         cursor.execute("SELECT LEVEL, SUBJECT ,COUNT(*) AS TOTAL FROM books WHERE IS_PAPER=0 GROUP BY LEVEL,SUBJECT")
#         result=cursor.fetchall()
#         #---------------organizing-------------------
#         for row in result:
#             key=f"{row['LEVEL']}_{row['SUBJECT']}"
#             counts[key]=row['TOTAL']
#         return counts
#     except Exception as err:
#         print(f"Error: {err}")
#         return {}
#     finally:
#         if connection and connection.is_connected():
#             cursor.close()
#             connection.close()

# #-----------calling the get book function------------
# book_counts=get_book_counts()
# print(f"The type of books counts is {type(book_counts)}")
# for book_count in book_counts:
#     print("="*50)
#     value=book_counts[book_count]
#     print(f"{book_count} {value}")

#phone number validation 
def Phonenumber_validation(phone,country="ZW"):
    if not phone or str(phone).strip()=="" :
        return "phone number is requiered"
    phone="".join(c for c in phone if c.isdigit() or c=="+")
    try:
        number=phonenumbers.parse(phone,country)
        if not phonenumbers.is_valid_number(number):
            print("Invalid phone number")
            return "Invalid phone number"
        return phonenumbers.format_number(number,phonenumbers.PhoneNumberFormat.E164).replace("+","")
    except phonenumbers.NumberParseException as e:
        print("Wrong phone number parsing method ",e)
        return "Wrong phone number parsing method ",e

#Email validation function 
def email_validation(email):
    if not email or email.strip()=="":
        return "Email is required"
    patt=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,3}$'
    pattern=re.compile(patt)
    if not bool(re.match(pattern,email)):
        return "Invalid email entered"
    return None


#Username validation
def validate_text(text):
    if not text or text.strip()=="":
        return "Username is required "
    patt=r'^[a-zA-Z][a-zA-Z0-9]{2,19}$'
    pattern=re.compile(patt)
    if not re.match(pattern,text):
        return "Invalid username has been entered"
    return None




#validating national identity number
def validate_nationl_id(ID_number):
    if not ID_number or ID_number.strip()=="":
        return "ID Number is required"
    patt = r'^[0-9]{2}([-\s]?)[0-9]{6,7}\1[a-zA-Z]\1[0-9]{2}$'
    if not bool(re.fullmatch(patt,ID_number)):
        return "Invalid ID number format entered"
    return True


    


    
    
if __name__=="__main__":
    import time
    import datetime
    #Testing the database connection 
    global_start_time=time.time()
    print(f"THE SCRIPT HAS STARTED NOW {datetime.datetime.now()}",flush=True)
    starts=time.time()
    testconn=Get_DbConnection()
    if testconn:
        print("="*80)
        print(f"DATABASE CONNECTION IS SUCCESFULL. DATABASE SERVER IS: {DB_HOST} AND USER IS: {DB_USER}")
        print("="*80)
        end_time=time.time()
        print(f"DATABASE CONNECTION ESTABLISHMENT TOOKS {end_time-starts:.4f}",flush=True)
        start=time.time()
        cusrsor=testconn.cursor()
        cusrsor.execute("SELECT 1")
        print(f"DATABASE QUERY RESPONSE: {time.time()-start:.4f} seconds",flush=True)
        print(f"THE TOTAL ELAPSED TIME IS {time.time()-global_start_time:.4f}")
    idnumber=input("Enter your ID number and press enter:")
    checkID=validate_nationl_id(idnumber)
    if checkID is False:
        print ("valid id number")
    else:
        print (checkID)

    errors=['Wrong phone number parsing method','Invalid phone number','phone number is requiered']
    formated_phone=None
    while True:
        phone=input("Enter phone number and press enter:")
        normalized_phone=Phonenumber_validation(phone)

        if normalized_phone  not  in errors:
            formated_phone=normalized_phone
            print(f"Correct phone number {formated_phone}")
            break    
        else:
            print(normalized_phone) 
        
    username=input("Enter your user name and press ENTER:")
    user=validate_text(username)
    if  user is not None :
        print( user )
    else:
        print("Valid username")

    email=input("Enter your email and press enter:")
    error=email_validation(email)
    if  error is True :
        print(error)
    else:
        print("Correct email has been entered:")

#------------Subjects normaalization function ------------
SUBJCT_MAP={'maths':'Mathematics','math':'Mathematics','mathematics':'Mathematics',
            'computer':'Computer Science', 'computers':'Computer Science','computer science':'Computer Science',
            'science':'Combined Science','sciences':'Combined Science','combined science':'Combined Science',
            'accounts':'Principles of Accounts','accounting':'Principles of Accounts','Principles of Accounts':'Principles of Accounts','account':'Principles of Accounts',
            'heritage':'Heritage Studies','heritage studies':'Heritage Studies','chem':'Chemistry','chemistry':'Chemistry',
            'crop':'Crop Science','crop science':'Crop Science','phy':'Physics','phys':'Physics','physics':'Physics',
            'stats':'Statistics','statistics':'Statistics','bio':'Biology','biology':'Biology','agric':'Agriculture','agric':'Agriculture','agriculture':'Agriculture',
            'geo':'Geography','geography':'Geography','hist':'History','history':'History','eng':'English','english':'English',
            'lits':'Literature in English','literature in english':'Literature in English','frs':'Family and Religious Studies','family and religious studies':'Family and Religious Studies',
            'se':'Software Engineering','software engineering':'Software Enginering','bes':'business studies'
            }
def normalized_subject(user_input):
    if not user_input:
        return None
    clean_userinput=user_input.lower().strip()
    return SUBJCT_MAP.get(clean_userinput,user_input.title())
SUBJECT_IMOJIS={'mathematics':'📐','computer science':'💻','combined science':'🔬','physics':'⚛️','chemistry':'⚗️','mechanics':'⚙️',
               'biology':'🧬','principles of accounts':'💰','crop science':'🌱' ,'software engineering':'👨‍💻','statistics':'📊',
               'geography':'🌍','french':'FR','shona':'📚','history':'📜','english':'📖','literature in shona':'📕','ndebele':'🗣️',
               'heritage studies':'🏛️','literature in english':'📚','family and religious studies':'⛪','economics':'📊',
               'agriculture':'🌾','commerce':'💼' ,'business studies':'💼'
              }

#--------------------file name cleaner---------------
def clean_filename(name: str):
   name=name.replace(" ","_")
   common_bad_chars=[(":","_"),("/","_"),("\\","_"),("|","_"),("*",""),("?",""),('"',"")]
   for bad,good in common_bad_chars:
       name=name.replace(bad,good)
   safe=''.join(c for c in name if c.isalnum() or c in "-_.")
   safe=safe.replace("--","-").replace("__","_").replace("..",".")
   while "__" in safe or "--" in safe or ".." in safe:
          safe=safe.replace("__","_")
          safe=safe.replace("--","-")
          safe=safe.replace("..",".")
   safe=safe.strip("-_.") 
   return safe if safe else  "unnamed_file" 


# subject=input("Enter subject: ")
# normalized_sub=normalized_subject(subject)
# print(f"THE entered subject is {subject} and it becomes {normalized_sub} after normalized")
           

        
