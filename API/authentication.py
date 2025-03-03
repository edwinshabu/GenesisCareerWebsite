from datetime import timedelta
from flask import Flask, app, request, jsonify, session
import re
from mysql.connector import Error
from database_connector import Connection, DBOperations
from alloperations import AllOperations
import base64
import mysql.connector



class Validation:
    def validate_email(email):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    def validate_contact(contact):
        contact_regex = r'^[0-9]{10}$'
        return re.match(contact_regex, contact) is not None

    def validate_password(password):
        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
        return re.match(password_regex, password) is not None

class Operations:

    def Authentication(username, password):
        try:
            conn, status = Connection.get_db_connection('root', 'Root@123')
            if status != 200:
                return "Error Occured during the Connection of Database. Contact Admin", 500
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT 1
            FROM users
            WHERE username = %s AND password = %s;
            """
            cursor.execute(query, (username, password))
            result = cursor.fetchone()
            if not result:
                return "User is not registered!", 404
            else:
                return result, 200
        except Error as e:
            print(e)
            return "Database Authentication server failed. Contact Admin", 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()


    def Login(username, password):
        

        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400

        connection, status = Connection.get_db_connection(username,password)
        if status != 200:
            return jsonify({'message': 'Either User is not registered or Credentials are incorrect.'}), status
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM Users WHERE Username = %s"
            cursor.execute(query, (username,))
            
            result = cursor.fetchone()
            if result:
                usertype, s = AllOperations.CheckUserType(username)
                if s == 200:
                    cursor.close()
                    connection.close() 
                    return jsonify({'message': 'Login successful', 'First Name': result['FirstName'], 'Last Name' : result['LastName'], 'UserType' : usertype }), 200
                else:
                    return jsonify({'message' : f"{usertype}"}), s
            else:
                cursor.close()
                connection.close() 
                return jsonify({'message': 'User is not Authorized.'}), 401
        except Error as e:
            cursor.close()
            connection.close() 
            return jsonify({'message': "Login Service Failed!. Please contact Administrator."}), 500


    def Check_User(username):
        try:
            conn, status = Connection.get_db_connection('root', 'Root@123')
            if status != 200:
                return "Unable to connect to Database to check User existence. Contact Admin.", status
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM mysql.user WHERE user = '{username}';")
            result = cursor.fetchone()
            if result[0] > 0:
                return "User exists!", 400
            else:
                return "Not Exists!", 200
        except:
            return "Unable to connect to Database to check User existence. Contact Admin.", 500
    
    def RollbackUser(username):
        try:
            conn, status = Connection.get_db_connection('root', 'Root@123')
            if status != 200:
                return jsonify({"message": f'{conn}'}), status
            cursor = conn.cursor()

            cursor.execute(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{username}'@'%';")
            cursor.execute(f"DROP USER IF EXISTS '{username}'@'%';")
            
            cursor.execute("FLUSH PRIVILEGES;")
            conn.commit()

            return {"message": f"User '{username}' has been rolled back successfully."}, 200

        except Exception as e:
            return {"message": f"Failed to rollback user '{username}': {str(e)}"}, 500

        finally:
            if 'conn' in locals():
                cursor.close()
                conn.close()

    
    def Create_NewUser(username, password):
        try:
            checking, stats = Operations.Check_User(username)
            if stats != 200:
                return checking, stats
            conn, status = Connection.get_db_connection('root', 'Root@123')
            if status != 200:
                return conn, status
            cursor = conn.cursor()
            cursor.execute(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}';")
        
            cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {'GenesisCareer'}.* TO '{username}'@'%';")
            
            cursor.execute("FLUSH PRIVILEGES;")
            conn.commit()
            
            
            return jsonify({"message": f"User {username}registerd."}), 200
        
        except Exception as e:
            return jsonify({"message":"Unable to create a new user. Please contact admin."}), 400
        
    def Session(username):
        try: 
            session['username'] = username 
            return session
        except Exception as e:
            return None
        
    def Register(data):
        required_fields = ['FirstName', 'LastName', 'EmailId', 'ContactDetails', 'UserType', 'SkillSet', 'Organization']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"{field} is required"}), 400
        profile_picture = request.files.get('ProfilePicture')
        resume = request.files.get('Resume')
            
        profile_picture_blob = None
        if profile_picture:
            profile_picture_blob = profile_picture.read()
        elif not profile_picture:
            return jsonify({"message":"Profile Picture is needed."}),400
    

        resume_blob = None
        if resume:
            resume_blob = resume.read()
        elif not resume:
            return jsonify({"message":"Resume is needed."}),404
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith("Basic "):
            base64_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(base64_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
        else:
            return jsonify({"message": "Authentication header is missing."}), 400
        first_name = data.get('FirstName')
        last_name = data.get('LastName')
        email = data.get('EmailId')
        username = username
        password = password
        contact = data.get('ContactDetails')
        user_type = data.get('UserType')
        skill_set = data.get('SkillSet')
        org = data.get('Organization')
        
        if not Validation.validate_email(email):
            return jsonify({"message": "Invalid email format"}), 400
        if not Validation.validate_contact(contact):
            return jsonify({"message": "Invalid contact number"}), 400
        if not Validation.validate_password(password):
            return jsonify({"message": "Invalid Password"}), 400
        
        result, status_code = Operations.Create_NewUser(username, password)
        if status_code != 200:
            return jsonify({"message": result}), status_code
        
        conn, status = Connection.get_db_connection(username, password)
        if status != 200:
            Operations.RollbackUser(username)
            return jsonify({"message":f"{conn}"}), status
        cursor = conn.cursor()
        try:    
     


            user_type_id, stat = DBOperations.GetUserType(username, password, user_type)
            if stat != 200:
                Operations.RollbackUser(username)
                return jsonify({"message": user_type_id}), stat

            

            cursor.execute(f"SELECT Id FROM Organization WHERE Name = '{org}';")
            org_id_data = cursor.fetchone()
            org_id = org_id_data[0]
            cursor.execute(""" 
                INSERT INTO Users (FirstName, LastName, Email, Username, Password, Contact, ProfilePic, Resume, Skills, UserTypeId, OrganizationId)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (first_name, last_name, email, username, password, contact, profile_picture_blob, resume_blob, skill_set, user_type_id, org_id))

            conn.commit()
            return jsonify({"message": "Registration successful"}), 200
        except mysql.connector.Error as err:
                conn.rollback()
                Operations.RollbackUser(username)
                return jsonify({"message": err.msg}), 500
        finally:
            cursor.close()
            conn.close()

    def ForgotPassword(username, emailId):
        try:
            connection, status = Connection.get_db_connection('root', 'Root@123')
            if status != 200:
                return connection, status
            cursor = connection.cursor()
            query = "SELECT password FROM Users WHERE username = %s AND email = %s"
            cursor.execute(query, (username, emailId))
            result = cursor.fetchone()
            if result == None:
                return "Username or Email is not registered.", 400
            if result:
                password = result[0]
                message = f"""
    Hello {username},

    This is your password for the Genesis Career Login.

    Password: '{password}'

    Regards,
    """
                if  AllOperations.SendEmail(emailId, message):
                    return "Password sent to email successfully", 200

            
        except Exception as ex:
            return f"An error occurred: {str(ex)}", 500
