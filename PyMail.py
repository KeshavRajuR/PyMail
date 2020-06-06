import os
import sys
import re
import click
import six
from PyInquirer import (Token, ValidationError, Validator,
                        print_json, prompt, style_from_dict)
from pyfiglet import figlet_format

try:
    import colorama
    colorama.init()
except ImportError:
    colorama = None

try:
    from termcolor import colored
except ImportError:
    colored = None


from validate_email import validate_email  # Used for validating provided emails
import smtplib  # Used for login and sending emails
from email.mime.multipart import MIMEMultipart  # Used in file attachments
from email.mime.text import MIMEText  # Used for making the body and other text based inputs in the mail
from email.mime.base import MIMEBase  # User in file attachments
from email import encoders

session = smtplib.SMTP_SSL('smtp.gmail.com', 465)
session.set_debuglevel(False)  # Shows communication with the server. Set to True to see communication

style = style_from_dict({
    Token.QuestionMark: '#fac731 bold',
    Token.Answer: '#4688f1 bold',
    Token.Instruction: '',  # default
    Token.Separator: '#cc5454',
    Token.Selected: '#0abf5b',  # default
    Token.Pointer: '#673ab7 bold',
    Token.Question: '',
})

def log(string, color = "white", text_font = "", figlet_font = "slant", figlet=False):
    if colored:
        if not figlet:
            if len(text_font):
                six.print_(colored(string, color, attrs=[text_font]))
            else:
                six.print_(colored(string, color))
        else:
            six.print_(colored(figlet_format(
                string, font=figlet_font), color))
    else:
        six.print_(string)


class EmailValidator(Validator):
    pattern = r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?"
    def validate(self, email):
        if len(email.text):
            if re.match(self.pattern, email.text):
                is_vaild = validate_email(email.text, verify=True)
                if is_vaild == True:
                    return True
                else:
                    raise ValidationError(
                        message="Email doesn't Exist",
                        cursor_position=len(email.text))
            else:
                raise ValidationError(
                    message="Invalid email",
                    cursor_position=len(email.text))
        else:
            raise ValidationError(
                message="You can't leave this blank",
                cursor_position=len(email.text))


class passValidator(Validator):
    pattern = r"((?=.*\d)|(?=.*[a-z])|(?=.*[A-Z])|(?=.*[@#$%]).{6,20})"
    def validate(self, password):
        if len(password.text):
            if re.match(self.pattern, password.text):
                return True
            else:
                raise ValidationError(
                    message="Invalid password",
                    cursor_position=len(password.text))
        else:
            raise ValidationError(
                message="You can't leave this blank",
                cursor_position=len(password.text))


class EmptyValidator(Validator):
    def validate(self, value):
        if len(value.text):
            return True
        else:
            raise ValidationError(
                message="You can't leave this blank",
                cursor_position=len(value.text))


class FilePathValidator(Validator):
    def validate(self, value):
        if len(value.text):
            if os.path.isfile(value.text):
                return True
            else:
                raise ValidationError(
                    message="File not found",
                    cursor_position=len(value.text))
        else:
            raise ValidationError(
                message="You can't leave this blank",
                cursor_position=len(value.text))


def getContentType(answer, conttype):
    return answer.get("content_type").lower() == conttype.lower()


def loginUser(from_email, password):
    try:
        session.login(from_email, password)
        return True
    except Exception:
        return False


def sendMail(from_email, recipients, files, mailinfo):
    email = MIMEMultipart()
    email['From'] = from_email
    email['To'] = mailinfo.get("to_email")
    email['To'] = ", ".join(recipients)
    email['Subject'] = mailinfo.get("subject")
    email.attach(MIMEText(mailinfo.get("content")))

    for file in files:
        filename = os.path.basename(file.split("/")[-1])
        attachement = open(file, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachement.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachement; filename=%s" % filename)
        email.attach(part)

    try:
        session.sendmail(from_email, recipients, email.as_string())
        session.quit()
        return True
    except Exception as err:
        log(err, color="red")
        return False


def askEmailInformation():
    questions = [
        {
            'type': 'input',
            'name': 'subject',
            'message': 'Subject:',
            'validate': EmptyValidator
        },
        {
            'type': 'list',
            'name': 'content_type',
            'message': 'Content type for body:',
            'choices': ['Text', 'HTML'],
            'filter': lambda val: val.lower()
        },
        {
            'type': 'input',
            'name': 'content',
            'message': 'Enter plain text:',
            'when': lambda answers: getContentType(answers, "text"),
            'validate': EmptyValidator
        },
        {
            'type': 'confirm',
            'name': 'confirm_content',
            'message': 'Do you want to send an html file:',
            'when': lambda answers: getContentType(answers, "html")
        },
        {
            'type': 'input',
            'name': 'content',
            'message': 'Enter html:',
            'when': lambda answers: not answers.get("confirm_content", True),
            'validate': EmptyValidator
        },
        {
            'type': 'input',
            'name': 'content',
            'message': 'Enter html file path:',
            'when': lambda answers: answers.get("confirm_content", False),
            'filter': lambda val: open(val).read(),
            'validate': FilePathValidator
        },
        {
            'type': 'confirm',
            'name': 'send',
            'message': 'Do you want to send now?'
        }
    ]

    answers = prompt(questions, style=style)
    return answers


def filesToAttach():
    questionsFiles = [
        {
            'type': 'confirm',
            'name': 'attach_file',
            'message': 'Do you want to attach a file?'
        },
        {
            'type': 'input',
            'name': 'attachment',
            'message': 'Enter filepath:',
            'when': lambda answersFiles: answersFiles["attach_file"] == True,
            'validate': FilePathValidator
        }
    ]

    answersFiles = prompt(questionsFiles, style=style)
    return answersFiles


def emailRecipients():
    questionsTo = [
        {
            'type': 'input',
            'name': 'to_email',
            'message': 'To Email:',
            'validate': EmailValidator
        },
        {
            'type': 'confirm',
            'name': 'add_receiver',
            'message': 'Do you want to add another receiver?'
        }
    ]

    answersTo = prompt(questionsTo, style=style)
    return answersTo


def askUserCreds():
    questionsAuth = [
        {
            'type': 'input',
            'name': 'from_email',
            'message': 'From Email:',
            'validate': EmailValidator
        },
        {
            'type': 'password',
            'name': 'password',
            'message': 'Enter your Email password:',
            'validate': passValidator
        }
    ]

    answersAuth = prompt(questionsAuth, style=style)
    return answersAuth


@click.command()
def main():
    """
    CLI built for sending mails using SMTP Protocol
    """

    ###Creating the welcome page, sorta###
    os.system('clear')

    log("PyMail CLI", color="blue", figlet=True)
    log("Welcome to PyMail CLI :)", color="green", text_font="bold")

    ###Getting and Authenticating User Credentials###
    password_count = 3

    while(bool(password_count)):
        user = askUserCreds()

        if (user.get("from_email") is not None and user.get("password") is not None):
            userAuthResponse = loginUser(user.get("from_email"), user.get("password"))
        else:
            sys.exit(0)

        if userAuthResponse:
            password_count = 0
            log("Login Successful!", color="green")
            break
        else:
            password_count -= 1
            log("Login failed! Number of retries left-", color="red")
            log(password_count, color="red", text_font="bold")

    if (userAuthResponse == False and bool(password_count) == False):  # Complete termination when canceled by user
        log("Too many attempts. Try again later...", color="red")
        sys.exit(0)

    ###Getting the receiver/s of the mail###
    recipients = []

    senderInfo = emailRecipients()

    while(senderInfo.get("add_receiver", False)):
        recipients.append(senderInfo.get("to_email"))
        senderInfo = emailRecipients()

    recipients.append(senderInfo.get("to_email"))

    recipients = list(dict.fromkeys(recipients))  # Remove duplicates

    if (bool(senderInfo) == False and recipients[0] == None):  # Complete termination when canceled by user
        sys.exit(0)

    ###Getting file attachements###
    files = []

    fileAttach = filesToAttach()

    while(fileAttach.get("attach_file", False)):
        files.append(fileAttach.get("attachment"))
        fileAttach = filesToAttach()

    files = list(dict.fromkeys(files))  #  Remove duplicates

    if (bool(fileAttach) == False and not files):  # Complete termination when canceled by user
        sys.exit(0)

    ###Getting the contents of the email###
    mailinfo = askEmailInformation()

    if mailinfo.get("send", False):
        response = sendMail(user.get("from_email"), recipients, files, mailinfo)
        if response == True:
            log("Email sent!", color="green")
        else:
            log("Could not send email", color="red")


if __name__ == '__main__':
    main()
