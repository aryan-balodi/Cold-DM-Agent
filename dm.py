from instagrapi import Client
import csv, time, random, json
import getpass

# —– User Input for Credentials —–
USER = input("Enter your Instagram username: ")
PASS = getpass.getpass("Enter your Instagram password: ")
SFILE = "session.json"

cl = Client()
try:
    # try loading saved session
    cl.load_settings(SFILE)
    cl.login(USER, PASS)
    print("✅ Logged in via session")
except Exception as e:
    print(f"Session login failed: {e}")
    # fresh login (handles 2FA if required)
    cl.login(USER, PASS)
    print("✅ Logged in fresh")

# save session for next run
with open(SFILE, "w") as f:
    json.dump(cl.get_settings(), f)

# —– Test DM Send —–
# Put one or two test usernames in targets.csv first:
# username,message
# your_own_username,Hello from instagrapi test!
with open("targets.csv", newline="", encoding="utf-8") as f:
    for username, message in csv.reader(f):
        try:
            user = cl.user_info_by_username_v1(username)
            uid = user.pk
            cl.direct_send(message, [uid])
            print(f"✔️  DM sent to {username}")
        except Exception as e:
            print(f"❌  Failed for {username}: {e}")
        time.sleep(random.uniform(30, 60))  # throttle
