"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase #exc = exception class in SQL ALCHEMY

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_invalid_message(self):
        """ Test adding a message with invalid data """
    
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/messages/new")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            # form displayed again?
            self.assertIn('Add my message!</button>', html)

            # correct error message?
            self.assertIn('This field is required.', html)


    def test_add_message_unauthorized(self):
        """ Test adding a message when not logged in """

        with self.client as c:
            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized.', html)
            
    def test_show_message(self):
        """ Test show message page """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
                
            m = Message(text="test message", user_id=self.testuser.id)
            db.session.add(m)
            db.session.commit()

            resp = c.get(f"/messages/{m.id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('test message', html)

    def test_show_invalid_message(self):
        """ Test show message with invalid id """

        with self.client as c:

            resp = c.get(f"/messages/9999")

            self.assertEqual(resp.status_code, 404)

    def test_delete_message(self):
        """ Test deleting a message """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            m = Message(id=1234, text="test message", user_id=self.testuser.id)
            db.session.add(m)
            db.session.commit()

            resp = c.post(f"/messages/{m.id}/delete", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)     

            # is message still in db?
            self.assertIsNone(Message.query.get(1234))

    def test_delete_invalid_message(self):
        """ Test delete on message with invalid id """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(f"/messages/999999/delete")

            self.assertEqual(resp.status_code, 404)


    def test_delete_message_logged_out(self):
        """ Test delete message while logged out """

        m = Message(id=1234, text="test message", user_id=self.testuser.id)
        db.session.add(m)
        db.session.commit()

        with self.client as c:
                
            resp = c.post(f"/messages/1234/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized.', html)   



    # TODO: Why is user2.id defined but not m.id??
    
    def test_delete_message_unauthorized(self):
        """ Test delete message while logged in as another user """

        user2 = User.signup("test2", "email", "password", "url")

        m = Message(id=1234, text="test message", user_id=self.testuser.id)
        db.session.add(m)
        db.session.commit()

        m = Message.query.get(1234)
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = user2.id

            resp = c.post(f"/messages/{m.id}/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)


            self.assertEqual(resp.status_code, 200)
            # self.assertIn('Access unauthorized.', html)            
            

