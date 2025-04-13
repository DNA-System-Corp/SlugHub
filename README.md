SlugHub
David Glover, Armando Barron, Spencer Johnson
SlugHub is your all-in-one companion app for navigating life as a UCSC student. Designed with usability and practicality in mind, SlugHub features robust user authentication with secure password encryption. Users can create multiple accounts on a single device and seamlessly switch between them, with each user’s data kept securely isolated. During registration, SlugHub ensures that each username and email is unique. Passwords must be at least 8 characters long and are securely encrypted before being stored in our MongoDB database.
Upon logging in, users are welcomed by a homepage with five main features:
	1.	Class Schedule
Students can input their class schedules using a dropdown menu preloaded with UCSC’s standardized time blocks. For added flexibility, an “Other…” option allows for custom time entries. Each added class appears as a colored block on the schedule. Classes can be easily added or removed using live-updating buttons that sync directly with the database.
	2.	Student Resources Directory
This page provides quick access to commonly used UCSC student resources through a curated list of helpful hyperlinks.
	3.	Interactive Campus Map
Automatically routes you to your next class based on the current date and time. You can switch between different travel modes, including walking, biking, driving, and public transportation. Users can also scroll through their upcoming classes and return to the current one with intuitive navigation buttons.
	4.	UCSC Events Page
Powered by BeautifulSoup and requests, this page scrapes live event data happening around UCSC. Users can:
	•	Pin events to keep them at the top of the list (pinned events also change color and can be unpinned with another click).
	•	Hide events, which removes them and allows space for new ones (each user sees a maximum of 15 events for optimal performance).
	•	Add to 📆: This adds the event to your schedule (displayed in a distinct color) and integrates with the interactive map features.
	5.	Class Forums
An anonymous, real-time forum system where students can join or create chatrooms for their classes. Posts appear instantly with no need for manual refresh, and all data is securely stored in the database. Forums are organized by department and course number, allowing for easy navigation and participation.


Prize Tracks:
	•	Education
	•	Slug Hack
	•	MongoDB Sponsor

