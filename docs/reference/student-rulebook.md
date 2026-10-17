# ECHO student rulebook — demo reference

**Fictional demonstration material, not official FAST NUCES policy.** All numbers, processes and deadlines in this dataset are sample rules for testing ECHO. Obtain an approved institutional handbook before using the system for real student decisions. Existing sample rules are retained; the expanded rules are invented demo content. Organizational names and contacts in the seed data are illustrative.

This edition contains 41 public policy entries and one protected access-control fixture. The protected fixture is excluded from retrieval and from this public reference.

## How this reference is used

`data/sample_policies.json` is the ingestion source of truth. This Markdown document is its readable public companion. Each policy is a self-contained retrieval unit. `data/sample_org.json` defines department routing and related-policy links. Apply changes using the offline bootstrap; editing this document alone does not update the database.

Times are working days unless the individual rule explicitly states calendar days or semester weeks. No current academic calendar, student account records or individual approval decisions are supplied. The existing fee rule leaves days 8–14 after its deadline unspecified; questions about that gap must go to staff. Attendance waiver document lists and upload locations are deliberately unspecified to demonstrate evidence-based escalation.

## Fees

### Semester Fee Payment Deadline

Reference: `fee-deadline-001` · Responsible office: Finance Office

Tuition fees for each semester must be paid by the 15th of the first month of the semester. A late fee of PKR 2,000 applies for payments made within 7 days after the deadline. Students who have not paid within 14 days after the deadline will have their course registration cancelled automatically.

### Payment Receipts and Unposted Payments

Reference: `fee-receipt-001` · Responsible office: Finance Office

After paying semester tuition, keep the bank receipt or electronic transaction reference. Allow two working days for the payment to appear in the student portal. If it is still missing, send the Finance Office your student ID, semester, payment date, amount and receipt. Only Finance can confirm or correct an individual payment record.

### Tuition Installment Requests

Reference: `fee-installments-001` · Responsible office: Finance Office

Students seeking tuition installments must submit an installment request to the Finance Office before the semester fee deadline. Include the current fee voucher and a brief explanation of the financial difficulty. Applying does not extend the payment deadline or establish approval. Finance issues any approved installment schedule in writing.

### Tuition Refund Requests

Reference: `fee-refund-001` · Responsible office: Finance Office

For the demo refund schedule, withdrawal from the semester during the first seven calendar days of classes qualifies for a full tuition refund; days eight through fourteen qualify for half of tuition; after day fourteen no tuition refund is available. Admission and application charges are non-refundable. Submit a refund form and payment receipt to Finance; Finance verifies eligibility and payment details before issuing a refund.

### Need-Based Financial Assistance

Reference: `fee-scholarship-001` · Responsible office: Finance Office

Need-based financial assistance applications are submitted to the Finance Office within the first ten working days of a semester. Submit the assistance form, household income evidence and the current fee voucher. Assistance is reviewed by a committee and is not guaranteed. Current award amounts and individual decisions are not published in the public rulebook.

### Incorrect Fee Voucher

Reference: `fee-voucher-001` · Responsible office: Finance Office

If the tuition voucher shows an incorrect course load or charge, contact Finance before the payment deadline with your student ID, the voucher and evidence of your registered courses. Students must not alter a bank voucher themselves. A correction request alone does not suspend the deadline; Finance must confirm any revised voucher or extension.

## Registration

### Late Course Registration Policy

Reference: `registration-late-001` · Responsible office: Registrar's Office

Students may register for courses up to 5 working days after the official registration period closes, subject to a late registration fee of PKR 1,500. After this grace period, course registration requires written approval from the Head of Department.

### Course Prerequisites

Reference: `registration-prerequisite-001` · Responsible office: Computer Science

A prerequisite course must be passed before a student can register for its dependent course. A portal error does not waive a prerequisite. If a completed prerequisite is missing from the record, provide the department office with the course codes and transcript evidence for review. The assistant cannot override prerequisite checks.

### Semester Credit Load

Reference: `registration-load-001` · Responsible office: Computer Science

The normal undergraduate semester load is 15 to 18 credit hours. A load above 18 and up to 21 credit hours requires written approval from the Head of Department before registration closes. Loads above 21 credit hours are not allowed under the demo rulebook. Approval depends on academic standing and course availability.

### Adding and Dropping Courses

Reference: `registration-add-drop-001` · Responsible office: Registrar's Office

The add and drop window is five working days long, starting on the first day of classes. Students can add or drop courses during this period if seats, prerequisites and timetables permit. After the window, adding requires written Head of Department approval. Later course removal follows the Course Withdrawal Policy. A dropped course does not guarantee a tuition refund.

### Timetable Clashes

Reference: `registration-clash-001` · Responsible office: Computer Science

Students must not register for courses whose scheduled teaching sessions overlap. Report a timetable clash to the department office with both course codes, section numbers and the overlapping session times. A requested section change is not effective until the portal registration has been updated by authorized staff.

### Full Sections and Waitlists

Reference: `registration-waitlist-001` · Responsible office: Computer Science

If a course section is full, request placement on the department waitlist during the registration period. Waitlisting is not enrollment, does not reserve a seat and does not authorize attendance as a registered student. The department contacts students if seats become available; confirm the final registered section in the portal.

### Semester Freeze Requests

Reference: `registration-freeze-001` · Responsible office: Registrar's Office

A student may request a semester freeze before classes begin by submitting a reasoned application to the Registrar. A freeze requires written approval and is limited to two semesters over the degree under this demo rulebook. The Registrar must confirm effects on degree completion time, scholarships and fees for the individual case.

## Attendance

### Minimum Attendance Requirement

Reference: `attendance-001` · Responsible office: Registrar's Office

Students must maintain at least 80% attendance in each course to be eligible to sit the final examination. Students falling below this threshold may request an attendance waiver from the course instructor only in documented medical or emergency cases.

### Incorrect Attendance Entries

Reference: `attendance-correction-001` · Responsible office: Computer Science

Report an incorrect attendance entry to the course instructor within five working days of the affected class. State the course, section, class date and why the entry appears incorrect. Only the instructor or authorized academic staff can verify and amend attendance. Submitting a correction request does not itself change final-examination eligibility.

### Laboratory Attendance

Reference: `attendance-lab-001` · Responsible office: Computer Science

Where a course has separate lecture and laboratory components, the demo 80 percent attendance requirement applies separately to each component. Good lecture attendance does not compensate for insufficient laboratory attendance. Any medical or emergency exception requires review; the assistant cannot grant a waiver.

## Courses

### Course Withdrawal Policy

Reference: `course-withdrawal-001` · Responsible office: Registrar's Office

Students may withdraw from a course without academic penalty up to the end of week 6 of the semester. Withdrawals after week 6 but before week 12 will be recorded as 'W' on the transcript. Withdrawals are not permitted after week 12.

### Final Examination Identification

Reference: `exam-id-001` · Responsible office: Registrar's Office

Bring a valid university student ID and the issued examination admit card to each final examination. Arrive at the assigned room at least twenty minutes before the scheduled start. If an ID card is lost, contact the Registrar before the exam for an identity-verification arrangement; an assistant response is not an entry permit.

### Missed Examination Requests

Reference: `exam-missed-001` · Responsible office: Computer Science

If a student misses an examination because of illness or an emergency, notify the department office as soon as possible and submit a written request with supporting evidence within two working days of the examination. A make-up examination requires approval from the examination committee. Dates, eligibility and outcomes are decided by staff and are not guaranteed by submitting a request.

### Examination Devices and Materials

Reference: `exam-devices-001` · Responsible office: Computer Science

Phones, smartwatches, earbuds and other communication devices must be switched off and stored as directed by invigilators before an examination. Calculators, printed notes or reference sheets may be used only when the examination instructions expressly permit them. An open-book designation does not automatically allow internet access or messaging.

### Assessment Mark Review

Reference: `grade-review-001` · Responsible office: Computer Science

A student may request review of an assessment mark within five working days after marks are published. Contact the course instructor first and identify the assessment and the suspected marking or totaling issue. A review checks for errors and does not guarantee an increase. Unresolved issues may be referred to the Head of Department.

### Incomplete Course Grades

Reference: `grade-incomplete-001` · Responsible office: Computer Science

An incomplete grade may be requested when documented exceptional circumstances prevent completion of a small remaining part of a course. Submit the request to the instructor before final grades are finalized. An approved request must specify remaining work and a completion deadline in writing. An incomplete grade is not an automatic alternative to a failing grade.

### Repeating a Failed Course

Reference: `course-repeat-001` · Responsible office: Computer Science

A failed compulsory course must be repeated when it is next available, subject to the approved study plan and prerequisites. Repeating does not erase the historical attempt from the transcript. The department confirms how a repeated course affects the individual degree audit and grade-point calculation.

### Academic Probation and Advising

Reference: `academic-standing-001` · Responsible office: Computer Science

Under this demo rulebook, a cumulative GPA below 2.00 places an undergraduate student on academic probation. A student on probation must meet an academic advisor before the next registration and agree on a study plan. The advisor confirms the permitted course load. Individual dismissal decisions and exceptions require formal staff review.

### Academic Integrity and AI Use

Reference: `academic-integrity-001` · Responsible office: Computer Science

Submit your own work and acknowledge external sources. Collaboration, code reuse and generative AI tools are permitted only to the extent stated in the course or assignment instructions. If those instructions are unclear, ask the instructor before using such assistance. The assistant cannot grant permission for an assignment or decide an individual misconduct case.

### Official Transcript Requests

Reference: `transcript-request-001` · Responsible office: Registrar's Office

Request an official transcript through the Registrar using the transcript request form, student ID and proof of the transcript processing charge. Normal processing is five working days after a complete request and required clearances are received. A portal grade screenshot is not an official transcript. Urgent processing requires staff confirmation.

### Graduation Clearance

Reference: `graduation-clearance-001` · Responsible office: Registrar's Office

Before a degree certificate can be issued, the student must complete academic requirements and obtain Finance, Library, laboratory and Registrar clearances. Start the clearance request through the Registrar after final results are published. The assistant may explain the process but cannot certify that a particular student has graduated or cleared outstanding dues.

### Transfer Credit Evaluation

Reference: `transfer-credit-001` · Responsible office: Computer Science

Transfer credit requires a formal department review of an official transcript, detailed course outlines and the previous institution information. Only courses approved as equivalent count toward the degree. A similar course name does not establish equivalence. The department issues the decision; the assistant cannot promise acceptance or estimate an individual transfer total.

### Internship Approval and Evidence

Reference: `internship-001` · Responsible office: Computer Science

Before starting an internship intended for academic credit, obtain department approval of the employer, role, dates and proposed supervisor. After completion submit the supervisor evaluation and internship report according to the approved course instructions. An employment offer alone does not guarantee academic credit.

### Final-Year Project Proposals

Reference: `fyp-001` · Responsible office: Computer Science

Final-year project teams submit a proposal containing the problem statement, scope, deliverables, member roles, timeline and proposed supervisor before the department deadline. A supervisor must accept the project and the department must approve the proposal. Current submission dates and individual project approval results must be confirmed with the department.

## General

### Helpdesk Operating Hours

Reference: `general-helpdesk-001` · Responsible office: Registrar's Office

The student helpdesk is open Monday to Friday, 9:00 AM to 4:00 PM, excluding public holidays. Outside these hours, students can submit queries through the online portal for a response within 1 business day.

### Library Borrowing and Renewals

Reference: `library-loans-001` · Responsible office: Library Services

A registered undergraduate may borrow up to three standard library books at a time for fourteen calendar days. A book may be renewed once if no other reader has reserved it. Reference-only materials remain in the library. Ask Library Services about account-specific borrowing restrictions or disputed loans.

### Overdue and Lost Library Books

Reference: `library-overdue-001` · Responsible office: Library Services

The demo overdue fine is PKR 20 per standard book per calendar day after the due date. If a library book is lost or damaged, report it to Library Services immediately; Library staff determine replacement cost and any applicable processing charge. Paying an overdue fine alone does not settle a lost-book case.

### Student Portal Password Reset

Reference: `it-password-001` · Responsible office: IT Support

Use the Forgot Password option on the student portal with your registered university email address. If you cannot access that email, contact IT Support for identity verification. Never send a password, recovery code or one-time code through the helpdesk chat. Staff cannot ask the assistant to reveal your existing password.

### Campus Wi-Fi Support

Reference: `it-wifi-001` · Responsible office: IT Support

Connect to the student wireless network using the university-issued account. If sign-in fails, verify the account on the student portal and report the building, approximate time, device type and displayed error to IT Support. Do not share your password in the report. This rulebook does not publish network passwords or administrative credentials.

### Lost Student ID Cards

Reference: `student-id-001` · Responsible office: Registrar's Office

Report a lost university student ID to the Registrar promptly so the card can be marked lost. Request a replacement with your student number and identity verification; the demo replacement charge is PKR 500. A replacement request does not automatically provide examination access; ask the Registrar for a temporary verification arrangement.

### Changes to Student Contact Details

Reference: `student-details-001` · Responsible office: Registrar's Office

Legal name changes cannot be made directly through the helpdesk chat. Legal name, national identity information and date-of-birth changes require a correction request with supporting documents to the Registrar. Students may update their phone number and correspondence address in the portal. The helpdesk assistant cannot edit student records or verify that a change has been completed.

### Accessibility and Examination Accommodations

Reference: `accessibility-001` · Responsible office: Student Services

Students needing accessibility support should contact Student Services as early as possible, preferably at least ten working days before an examination or assessed activity. Provide the support request and relevant professional documentation through the staff-designated confidential channel. Approved accommodations are confirmed in writing; the assistant cannot approve extra time or collect medical records.

### Student Counseling Appointments

Reference: `counseling-001` · Responsible office: Student Services

Student Services arranges confidential counseling appointments during normal working days. Request an appointment through the student-services office and provide a preferred contact method and available times. Detailed counseling notes are not part of this public rulebook. This helpdesk chat is not an emergency response channel.

### Student Society Room Bookings

Reference: `room-booking-001` · Responsible office: Student Services

A registered student society may request a teaching room for an event at least five working days in advance. Send Student Services the society name, faculty advisor, event purpose, estimated attendance, requested room and time. A room is reserved only after written confirmation, and academic teaching takes priority.

### Academic Calendar and Unpublished Dates

Reference: `official-dates-001` · Responsible office: Registrar's Office

Semester-specific class start dates, examination timetables, holidays and application closing dates are published in the official academic calendar or relevant staff notice. This sample rulebook does not contain current calendar dates or live room schedules. If a date is not explicitly present in the supplied public policies, staff must confirm it rather than the assistant guessing.
