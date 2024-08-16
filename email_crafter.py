import json
from professor_data_handler import ProfessorDataHandler
from query_generator import QueryGenerator
from search_executor import SearchExecutor
from email_crafter import EmailCrafter
from email_sender import BrevoEmailSender
from prompts import student_info
from api_handler import LLM_APIHandler
from utils import get_utc_scheduled_time

from datetime import datetime, timedelta, timezone


def main():
    """
    Main function orchestrating the overall process from generating search queries to crafting emails.

    Process:
        1. Reads professor data from the database.
        2. For each professor record, generates search queries based on student interests.
        3. Executes these queries and retrieves results.
        4. Crafts an email based on search results and student preferences, and stores it in the professor record under 'Email'.
        5. Sends the email to the professor.
        6. Updates the database with the modified professor record.
    """

    model_choice = "gemini-pro"  # Choose between "gemini-pro" and "gpt-3.5-turbo"
    # model_choice = "gpt-3.5-turbo"  # Choose between "gemini-pro" and "gpt-3.5-turbo"

    # Read API keys
    key_path = r"C:\Users\bnsoh2\OneDrive - University of Nebraska-Lincoln\Documents\keys\api_keys.json"
    with open(key_path) as f:
        api_keys = json.load(f)
        PERPLEXITY_API_KEY = api_keys["PERPLEXITY_API_KEY"]
        BREVO_API_KEY = api_keys["BREVO_API_KEY"]

    # Initialize the API handler
    llm_handler = LLM_APIHandler(key_path)

    # Initialize the DatabaseSetupManager and set up the database path
    table_name = "professors"
    db_template_path = "professors_db_template.db"
    data_handler = ProfessorDataHandler(db_template_path, table_name)

    # Initialize other classes
    query_gen = QueryGenerator(llm_handler)
    search_exec = SearchExecutor(PERPLEXITY_API_KEY)
    email_crafter = EmailCrafter(llm_handler)
    email_sender = BrevoEmailSender(BREVO_API_KEY)

    # Process each professor record
    professor_records, db_path = data_handler.setup_database()
    print
    professor_records = [x for x in professor_records if x.get("Sent", 0) == 0]

    count = 0

    for record in professor_records:
        # Get and execute search queries
        updated_record = query_gen.use_predefined_query(record)
        print("Queries generated for", updated_record["Employee"])
        updated_record = search_exec.perform_search(updated_record)
        print("Queries executed for", updated_record["Employee"])

        # Craft email
        email_data = email_crafter.craft_email(
            student_info, updated_record, model_choice
        )
        email_body = email_data["body"]
        subject_line = email_data["subject"]

        email_to_send = {
            "Contact": updated_record["Contact"],
            "Email_To_Send": email_body,
            "Subject": subject_line,
            "Attachment_Path": r"C:\Users\bnsoh2\OneDrive - University of Nebraska-Lincoln\Documents\Coding Projects\Automated_Reachouts\Mambo_resume.pdf",
            "Sent": 0,
        }

        # specify the day and timezone. email is always sent at 8am
        # call the function, increment the minute by 1 for every 5 counts the loop goes through, reset to 0 after 50 minutes
        count += 1
        additional_minutes = (count // 5) % 10  # reset to 0 after 50 minutes
        utc_scheduled_time = get_utc_scheduled_time(
            17, "America/Chicago", 2024, 1, 8, additional_minutes
        )

        email_sender.send_email(
            [email_to_send], utc_scheduled_time
        )  # Send the email with the subject line

        # Update database
        full_email_content = f"Subject: {subject_line}\n\n{email_body}"
        updated_record["Email_To_Send"] = full_email_content
        updated_record["Sent"] = 1
        data_handler.update_database(updated_record, db_path)


if __name__ == "__main__":
    main()
