# Smart Campus Analytics — 3-5 Minute Competition Demonstration Storyboard

This script provides a 7-scene presentation outline with concise speaking notes for demonstrating the platform to judges and evaluators.

---

## 🎬 Demonstration Sequence & Speaking Notes

### Scene 1: The Problem (Duration: 30s)
- **Visual**: Show traditional fragmented spreadsheets or isolated campus systems.
- **Speaking Notes**:  
  *"Colleges collect massive amounts of student data—marks, attendance, LMS logins, placement scores—but it sits in isolated silos. By the time a student fails a semester or misses campus placements, it's too late for faculty to intervene. We built **Smart Campus Analytics** to solve this."*

---

### Scene 2: Institutional Executive Overview (Duration: 45s)
- **Visual**: Navigate to `http://127.0.0.1:8000/dashboard/`. Highlight summary KPI cards, Risk Distribution Chart, Department Comparisons, and Automated Insight Cards.
- **Speaking Notes**:  
  *"Our Executive Overview gives administrators instant decision intelligence across the campus. Here we see 43 enrolled students with an overall average success score of 78.4. Notice our automated insight card—it dynamically alerts us that 7 students are flagged with critical attendance deficits below 75%."*

---

### Scene 3: At-Risk Monitoring Workspace (Duration: 45s)
- **Visual**: Click **At-Risk Workspace** in the sidebar (`/risk-monitoring/`). Show the list of `HIGH` and `CRITICAL` risk students.
- **Speaking Notes**:  
  *"Rather than forcing faculty to dig through rows of data, our At-Risk Workspace isolates students needing immediate review. For instance, student STU2025002 is flagged for Critical Risk due to a low CGPA of 5.2 and an attendance rate of 62%."*

---

### Scene 4: Explainable Student Profile & Risk Drivers (Duration: 45s)
- **Visual**: Click **View Profile** on `STU2025002` (`/students/STU2025002/`). Show the **Explainable Score Contribution Matrix** and **Risk Drivers List**.
- **Speaking Notes**:  
  *"Here is our core innovation: **Explainable AI Scoring**. We don't just output a black-box number. Our contribution matrix shows the exact weight and sub-score for Academics (30%), Attendance (25%), LMS (15%), Placement (15%), and Skills (15%). Below, faculty can clearly see the empirical risk drivers triggering the classification."*

---

### Scene 5: Placement Readiness & Skill Gap Identification (Duration: 45s)
- **Visual**: Navigate to **Placement Readiness Tab** for a Group C student (`STU2025003`). Show high CGPA ($9.1$) alongside a low coding score ($42\%$).
- **Speaking Notes**:  
  *"Our platform distinguishes academic performance from career readiness. Here is a student with an outstanding 9.1 CGPA, but their coding assessment score is only 42%. Placement officers can immediately spot this gap before company drives begin."*

---

### Scene 6: Closed-Loop Intervention Workflow (Duration: 45s)
- **Visual**: Click **Log Intervention** button. Select *Placement Skill Bootcamp*, enter reason, and click Save. Then show updating status to *Completed* on `/interventions/`.
- **Speaking Notes**:  
  *"Analytics are useless without action. With one click, faculty can log a targeted intervention—such as a Technical Skill Bootcamp—assign a counselor, set follow-up dates, and track resolution outcomes to completion."*

---

### Scene 7: Decision Intelligence Conclusion (Duration: 30s)
- **Visual**: Return to Executive Overview or Reports Export page (`/reports/`).
- **Speaking Notes**:  
  *"Smart Campus Analytics turns raw institutional data into closed-loop decision intelligence—empowering faculty, protecting student outcomes, and maximizing placement success."*
