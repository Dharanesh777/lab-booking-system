"""Synthetic dataset - PSG Tech CSE/AI Wing Lab Slot Booking System (v2, based on the REAL lab timetables).
Run: python generate_data.py   (fixed seed => reproducible)
Edit the TEMPLATES list below to correct anything I mis-read from the photos, then re-run."""
import csv, random, json, re
from datetime import date, timedelta
random.seed(7)
TODAY = date(2026, 10, 24)

# ---- 8 periods per day (from CC Lab 1 timetable photo) ----
PER = {1:("08:30","09:20"),2:("09:20","10:10"),3:("10:30","11:20"),4:("11:20","12:10"),
       5:("13:40","14:30"),6:("14:30","15:20"),7:("15:30","16:20"),8:("16:20","17:10")}
DAYS = ["Mon","Tue","Wed","Thu","Fri"]

# ---- LABS (the 8 labs from your timetable photos; 40-50 systems each) ----
labs = [
 (1,"Programming Lab 1","Programming",50,"available","CSE Block","Python, C, C++, Java, VS Code, MySQL"),
 (2,"3AI Lab","Programming",45,"available","AI Wing","Python, Java, C++, Jupyter"),
 (3,"Programming Lab II","Programming",50,"available","CSE Block","Python, C, C++, Java, VS Code"),
 (4,"AIR Lab","AI/ML",40,"available","AI Wing","Python, TensorFlow, PyTorch, Wireshark, GCC"),
 (5,"SCPS Lab","Systems & Networking",48,"available","CSE Block","Linux, GCC, Wireshark, Packet Tracer, NS-2"),
 (6,"TEQIP II Sponsored Hardware Lab","Hardware/Embedded",40,"available","CSE Block","Arduino IDE, Keil, Proteus, Embedded C"),
 (7,"CC Lab 1 (PSG Computer Centre)","Programming",50,"available","Computer Centre","C, C++, Code::Blocks"),
 (8,"GRD Computing Lab","AI/ML",50,"available","AI Wing","Python, TensorFlow, PyTorch, Spark, Hadoop, Jupyter"),
]
LAB = {l[0]: l for l in labs}

# ---- WEEKLY TIMETABLE TEMPLATES, read from the photos ----
# (lab, day, start_period, end_period, batch, subject, students, faculty, confidence, note)
# confidence: high = printed text clearly read; medium = printed but row/period position inferred;
#             low = handwritten / hard to read -> VERIFY
S="Staff"
T = [
 # Programming Lab 1
 (1,"Mon",5,8,"V Sem BE CSE (AI&ML)","Application Development Lab",35,None,"high",""),
 (1,"Tue",5,8,"III Sem BE CSE (AI&ML)","OOPS Lab",35,None,"high",""),
 (1,"Wed",5,8,"III Sem BE CSE (AI&ML)","DS Lab",35,None,"high",""),
 (1,"Thu",5,8,"V Sem BE CSE (AI&ML)","Big Data Analytics Lab",35,None,"high",""),
 (1,"Tue",1,2,S,"Staff reservation","Dr. K.G.S","low","handwritten; periods approximate"),
 (1,"Wed",1,4,S,"AI Lab (staff reservation)","Dr. Indumathi","low","handwritten; periods approximate"),
 (1,"Fri",3,4,S,"Staff reservation","Dr. K.G.S","low","handwritten; periods approximate"),
 # 3AI Lab
 (2,"Mon",1,4,"I Sem BE CSE G2","Python Lab",32,None,"medium",""),
 (2,"Mon",5,8,"III Sem BE CSE G1","OOPS Lab",32,None,"high",""),
 (2,"Tue",5,8,"I Sem BE CSE G2","Python Lab",32,None,"medium",""),
 (2,"Fri",5,8,"III Sem BE CSE G2","OOPS Lab",32,None,"low","handwritten; typed Thu entry looks overwritten"),
 # Programming Lab II
 (3,"Mon",1,4,"I Sem BE CSE (AI&ML)","Python Programming Lab",35,None,"high",""),
 (3,"Thu",5,8,"I Sem BE CSE (AI&ML)","Python Programming Lab",35,None,"high",""),
 (3,"Fri",5,8,S,"TAS Lab (staff reservation)","Priya M.S.","low","handwritten"),
 # AIR Lab
 (4,"Mon",1,4,"VII Sem BE CSE G2","CNS Lab",32,None,"high",""),
 (4,"Wed",1,4,"VII Sem BE CSE G1","CNS Lab",32,None,"high",""),
 (4,"Mon",5,8,"VII Sem BE CSE G1","PDL Lab",32,None,"high",""),
 (4,"Tue",5,8,"III Sem BE CSE G1","DS Lab",32,None,"high",""),
 (4,"Wed",5,8,"VII Sem BE CSE G2","PDL Lab",32,None,"high",""),
 (4,"Thu",5,8,"III Sem BE CSE G2","DS Lab",32,None,"high",""),
 (4,"Thu",1,4,S,"Staff reservation","Anil Jothi","low","handwritten; periods approximate"),
 (4,"Fri",1,4,S,"Staff reservation","Anil Jothi","low","handwritten; periods approximate"),
 # SCPS Lab
 (5,"Mon",1,4,"V Sem BE CSE G2","Computer Networks Lab",32,None,"high",""),
 (5,"Tue",1,4,"V Sem BE CSE (AI&ML)","Computer Networks Lab",35,None,"high",""),
 (5,"Wed",1,4,"V Sem BE CSE G1","Computer Networks Lab",32,None,"high",""),
 (5,"Tue",5,8,"V Sem BE CSE (CSI)","System Software Lab",30,None,"medium",""),
 (5,"Thu",1,4,"V Sem BE CSE (CSI)","System Software Lab",30,None,"medium",""),
 (5,"Thu",5,8,"V Sem BE CSE G2","System Software Lab",32,None,"high",""),
 (5,"Fri",5,8,"V Sem BE CSE G1","System Software Lab",32,None,"high",""),
 (5,"Fri",1,2,S,"Python (staff reservation)","JPK","low","handwritten"),
 (5,"Fri",3,4,S,"Staff reservation","K.G.S","low","handwritten"),
 (5,"Wed",5,8,S,"Staff reservation","K.G.S","low","handwritten"),
 # TEQIP II Sponsored Hardware Lab
 (6,"Mon",1,4,"I Sem BE CSE (AI&ML)","EP Lab",35,None,"high",""),
 (6,"Thu",5,8,"I Sem BE CSE (AI&ML)","EP Lab",35,None,"high",""),
 (6,"Tue",5,8,S,"Embedded Lab (staff reservation)","Dr. Shriranjani","low","handwritten; day inferred"),
 # CC Lab 1 (service lab for other departments)
 (7,"Tue",5,7,"III Sem Metallurgy","C Programming Lab",40,None,"medium",""),
 (7,"Wed",2,4,"II B.Sc (Applied Science)","C Programming Lab",35,None,"medium",""),
 (7,"Thu",3,4,"III Sem Metallurgy","C Programming Lab",40,None,"medium",""),
 (7,"Fri",5,7,"II B.Sc (Applied Science)","C Programming Lab",35,None,"medium","printed 'IIIB.Sc' or 'IIB.Sc' - verify"),
 # GRD Computing Lab
 (8,"Mon",5,8,"VII Sem BE CSE (AI&ML)","Project Work 1",35,None,"high",""),
 (8,"Tue",5,8,"VII Sem BE CSE G2","Project Work 1",32,None,"high",""),
 (8,"Wed",5,8,"VII Sem BE CSE G1","Project Work 1",32,None,"high",""),
 (8,"Thu",5,8,"V Sem BE CSE (AI&ML)","ML-2 Lab",35,None,"high","handwritten '69' = class strength; assumed 2 groups"),
 (8,"Tue",1,2,S,"Staff reservation","Dr. K.G.S","low","handwritten; periods approximate"),
]

SEMS = [("Odd 2025-26",date(2025,7,21),date(2025,11,29),"odd"),
        ("Even 2025-26",date(2026,1,5),date(2026,4,30),"even"),
        ("Odd 2026-27",date(2026,7,20),date(2026,11,28),"odd")]
CUR = "Odd 2026-27"
STAFF = ["Dr. A. Ramesh","Dr. S. Priya","Prof. M. Anand","Dr. N. Lakshmi","Prof. R. Karthik","Dr. V. Meena","Prof. B. Suresh","Dr. T. Divya"]

def w(name, header, rows):
    with open(f"{name}.csv","w",newline="") as f:
        cw = csv.writer(f); cw.writerow(header); cw.writerows(rows)

def sem_dates(a,b):
    d=a
    while d<=b:
        if d.weekday()<5: yield d
        d+=timedelta(days=1)
def pr(sp,ep): return set(range(sp,ep+1))

w("periods",["period_no","start_time","end_time"],[(k,)+v for k,v in PER.items()])
w("labs",["lab_id","name","lab_type","capacity","status","location","software_tags"],labs)

# ---- EQUIPMENT ----
equipment=[]; eid=[1]
def add(lab,name,cat,specs=""):
    equipment.append([eid[0],lab,f"AST-{lab:02d}-{eid[0]:04d}",name,cat,specs,"working",
        f"{random.randint(2019,2025)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"]); eid[0]+=1
for lid,name,ltype,cap,*_ in labs:
    for n in range(1,cap+1):
        add(lid,f"PC-L{lid:02d}-{n:02d}","PC","Intel i5, 16GB RAM, 512GB SSD" if ltype!="AI/ML" else "Intel i7, 32GB RAM, 1TB SSD")
    add(lid,f"Projector-L{lid:02d}","Projector","HDMI/VGA")
    add(lid,f"AC-L{lid:02d}-A","Air Conditioner","2 Ton"); add(lid,f"AC-L{lid:02d}-B","Air Conditioner","2 Ton")
    add(lid,f"Switch-L{lid:02d}","Networking Device","48-port managed switch")
    add(lid,f"UPS-L{lid:02d}","UPS","10 kVA")
    if ltype=="AI/ML":
        for g in (1,2): add(lid,f"GPU-Workstation-L{lid:02d}-{g}","GPU Workstation","RTX 4090 24GB, 64GB RAM")
    if ltype=="Hardware/Embedded":
        for kind,cat,q in [("Oscilloscope","Instrument",10),("Function-Generator","Instrument",10),("Arduino-Kit","IoT Kit",10),("RaspberryPi-Kit","IoT Kit",10),("FPGA-Board","Instrument",5)]:
            for n in range(1,q+1): add(lid,f"{kind}-L{lid:02d}-{n:02d}",cat)
EQ_BY_LAB={}
for e in equipment: EQ_BY_LAB.setdefault(e[1],[]).append(e)

# ---- SEMESTER TEMPLATES (3 semesters) ----
SEMMAP={"I":"II","III":"IV","V":"VI","VII":"VIII"}
SUBMAP={"II":"C Programming Lab","IV":"DBMS Lab","VI":"Machine Learning Lab","VIII":"Project Work 2"}
def even_version(batch,subj):
    p=batch.split(" ")
    if len(p)>1 and p[1]=="Sem" and p[0] in SEMMAP:
        n=SEMMAP[p[0]]; return " ".join([n]+p[1:]), SUBMAP[n]
    return batch,subj

templates=[]; tid=[1]
for label,a,b,kind in SEMS:
    placed={}                     # (lab,day)->set(periods)
    for row in T:
        if len(row)==9: row=row[:5]+(row[5],None)+row[6:]
        (lab,day,sp,ep,batch,subj,cnt,fac,conf,note)=row
        di=DAYS.index(day)
        if kind=="even" and batch!=S:
            batch,subj=even_version(batch,subj)
            opts=[max(0,min(4,di+random.choice([0,0,1,-1]))),di]
        else: opts=[di]
        # staff reservations only in current + previous odd semesters
        if kind=="even" and T and batch==S: continue
        for d_ in opts:
            if not (placed.get((lab,d_),set()) & pr(sp,ep)):
                placed.setdefault((lab,d_),set()).update(pr(sp,ep))
                locked = 0 if batch==S else 1
                templates.append(dict(tid=tid[0],lab=lab,day=DAYS[d_],sp=sp,ep=ep,batch=batch,subj=subj,cnt=cnt,fac=fac,
                    conf=conf,note=note,label=label,a=a,b=b,locked=locked,status="active" if label==CUR else "completed"))
                tid[0]+=1; break
w("semester_timetables",["template_id","assigned_lab_id","batch","subject","faculty","lab_type","student_count","day_of_week",
   "start_period","end_period","start_time","end_time","semester_label","semester_start","semester_end","is_locked","status","confidence","source_note"],
  [(t["tid"],t["lab"],t["batch"],t["subj"],t["fac"] or "",LAB[t["lab"]][2],t["cnt"] if t["cnt"] else "",t["day"],t["sp"],t["ep"],
    PER[t["sp"]][0],PER[t["ep"]][1],t["label"],t["a"],t["b"],t["locked"],t["status"],t["conf"],t["note"]) for t in templates])

# ---- BOOKINGS ----
occ={}   # (lab,date)->set(periods) for confirmed/completed
bookings=[]
def book(lab,d,sp,ep,batch,subj,fac,cnt,btype,prio,status,rec,a,b,lock,tid_,who):
    bookings.append([0,lab,d.isoformat(),PER[sp][0],PER[ep][1],sp,ep,batch,subj,fac or "",cnt if cnt else "",btype,prio,status,rec,
        a.isoformat() if a else "",b.isoformat() if b else "",int(lock),tid_ or "",who,(d-timedelta(days=random.randint(5,30))).isoformat()])
    if status in("confirmed","completed"): occ.setdefault((lab,d),set()).update(pr(sp,ep))

for t in templates:
    for d in sem_dates(t["a"],t["b"]):
        if DAYS[d.weekday()]!=t["day"]: continue
        st="confirmed" if d>=TODAY else ("cancelled" if random.random()<0.04 else "completed")
        book(t["lab"],d,t["sp"],t["ep"],t["batch"],t["subj"],t["fac"],t["cnt"],"semester",2,st,"weekly",t["a"],t["b"],t["locked"],t["tid"],t["fac"] or "Timetable Cell")

BLOCKS=[(1,4),(5,8),(1,2),(3,4),(5,6),(7,8),(5,7),(2,4)]
REASONS=[("ACM Student Chapter","Coding contest practice"),("Mini Project Team","Project review"),("Hackathon Team","Hackathon prep"),
         ("III Sem BE CSE G1","Makeup lab"),("V Sem BE CSE (AI&ML)","Extra practice session"),("VII Sem BE CSE G2","Internal lab exam"),
         ("Faculty Development Program","Workshop"),("CSE Association","Guest lecture demo")]
for label,a,b,kind in SEMS:
    ds=list(sem_dates(a,b)); n=0
    while n<60:
        d=random.choice(ds); lab=random.choice(labs); sp,ep=random.choice(BLOCKS); cnt=random.choice([15,20,25,30,35,40,45])
        if cnt>lab[3] or (occ.get((lab[0],d),set()) & pr(sp,ep)): continue
        st="completed" if d<TODAY else "confirmed"; r=random.random()
        if r<0.06: st="cancelled"
        elif r<0.10 and d>=TODAY: st="pending"
        batch,subj=random.choice(REASONS)
        book(lab[0],d,sp,ep,batch,subj,"",cnt,"regular",1,st,"none",None,None,0,None,random.choice(STAFF)); n+=1

COMP=["TCS NQT","Zoho Online Test","Infosys InfyTQ","Cognizant GenC","Accenture Assessment","Wipro NLTH","Freshworks Test","Mphasis Drive"]
for label,a,b,kind in SEMS:
    ds=list(sem_dates(a,b)); n=0
    while n<6:
        d=random.choice(ds); lab=random.choice(labs); sp,ep=random.choice([(1,4),(5,8)]); cnt=random.choice([40,45,48,50])
        if cnt>lab[3] or (occ.get((lab[0],d),set()) & pr(sp,ep)): continue
        book(lab[0],d,sp,ep,"Final Year Placement Group",random.choice(COMP),"",cnt,"placement",3,"completed" if d<TODAY else "confirmed","none",None,None,1,None,"Placement Cell"); n+=1

# demo: urgent pending placement requests that clash with LOCKED semester classes but have a free alternative lab
cands=[b for b in bookings if b[11]=="semester" and b[13]=="confirmed" and b[2]>="2026-11-02" and b[5]==5 and b[6]==8 and b[17]==1]
random.shuffle(cands); demo=[]
for b in cands:
    if len(demo)==3: break
    need=45
    if LAB[b[1]][3]<need: continue
    d=date.fromisoformat(b[2])
    alts=[l[0] for l in labs if l[0]!=b[1] and l[3]>=need and not (occ.get((l[0],d),set()) & pr(5,8))]
    if not alts or any(x[2]==b[2] for x in demo): continue
    book(b[1],d,5,8,"Final Year Placement Group","Zoho Online Test (URGENT)","",need,"placement",3,"pending","none",None,None,0,None,"Placement Cell")
    demo.append(bookings[-1]); occ[(b[1],d)]=occ[(b[1],d)]  # pending doesn't change occupancy
bookings.sort(key=lambda x:(x[2],x[3],x[1]))
for i,b in enumerate(bookings,1): b[0]=i
demo_ids=[b[0] for b in bookings if "URGENT" in b[8]]
w("bookings",["booking_id","lab_id","booking_date","start_time","end_time","start_period","end_period","batch","subject","faculty","student_count",
   "booking_type","priority","status","recurrence","semester_start","semester_end","is_locked","template_id","requested_by","created_at"],bookings)

# ---- FAULTS ----
descs={"PC":["System not booting","Monitor flickering","Keyboard not responding","Network card failure","Overheating / auto shutdown","Disk failure, slow performance","No display output"],
 "Projector":["Lamp failure","No HDMI signal","Colour distortion"],"Air Conditioner":["Not cooling","Water leakage","Unusual noise"],
 "Networking Device":["Port failure","Intermittent connectivity","Firmware crash"],"UPS":["Battery backup failure","Overload alarm"],
 "GPU Workstation":["CUDA driver crash","GPU overheating","GPU not detected"],"IoT Kit":["Sensor not responding","Board damaged"],
 "Instrument":["Probe damaged","Display fault","Calibration drift"]}
faults=[]
def addf(e,d,status):
    res=(d+timedelta(days=random.randint(1,6))).isoformat() if status=="resolved" else ""
    faults.append([0,e[0],random.choice(descs[e[4]]),d.isoformat(),status,res])
for _ in range(90): addf(random.choice(equipment),TODAY-timedelta(days=random.randint(31,330)),"resolved")
for _ in range(14): addf(random.choice(equipment),TODAY-timedelta(days=random.randint(1,29)),random.choice(["open","under_repair","resolved","resolved"]))
repeat=[EQ_BY_LAB[1][4],EQ_BY_LAB[4][11],EQ_BY_LAB[5][20],EQ_BY_LAB[8][2],
        next(e for e in EQ_BY_LAB[3] if e[4]=="Projector"),next(e for e in EQ_BY_LAB[7] if e[4]=="Networking Device")]
for e in repeat:
    for k in range(random.choice([3,4])): addf(e,TODAY-timedelta(days=random.randint(1,28)),"open" if k==0 else "resolved")
faults.sort(key=lambda x:x[3])
for i,f in enumerate(faults,1): f[0]=i
w("fault_reports",["fault_id","equipment_id","fault_description","fault_date","status","resolved_date"],faults)
openeq={f[1] for f in faults if f[4] in("open","under_repair")}; under={f[1] for f in faults if f[4]=="under_repair"}
for e in equipment: e[6]="under_repair" if e[0] in under else ("faulty" if e[0] in openeq else "working")
w("equipment",["equipment_id","lab_id","asset_tag","name","category","specs","status","purchase_date"],equipment)

# ---- TEST REQUESTS ----
c=[b for b in bookings if b[11]=="semester" and b[13]=="confirmed" and b[2]>="2026-11-02"][0]
json.dump({
 "conflicting_booking":{"lab_id":c[1],"booking_date":c[2],"start_time":c[3],"end_time":c[4],"batch":"V Sem BE CSE G1","student_count":30,"booking_type":"regular"},
 "insufficient_capacity":{"lab_id":4,"booking_date":"2026-11-17","start_time":"08:30","end_time":"10:10","batch":"V Sem BE CSE (AI&ML)","student_count":45,"booking_type":"regular"},
 "end_before_start":{"lab_id":1,"booking_date":"2026-11-17","start_time":"15:30","end_time":"13:40","batch":"V Sem BE CSE G1","student_count":30,"booking_type":"regular"},
 "unknown_lab":{"lab_id":99,"booking_date":"2026-11-17","start_time":"08:30","end_time":"10:10","batch":"V Sem BE CSE G1","student_count":30,"booking_type":"regular"},
 "placement_conflict_demo_booking_ids":demo_ids,
 "nl_examples":["I need a programming lab for 40 students on Thursday morning for two hours.",
                "Book a networking lab for 30 students next Monday afternoon.",
                "Need a GPU / AI lab for 35 students tomorrow from 1:40 PM to 3:20 PM."]},open("test_requests.json","w"),indent=2)
print("labs",len(labs),"equipment",len(equipment),"templates",len(templates),"bookings",len(bookings),"faults",len(faults))
print("demo:",[(b[0],LAB[b[1]][1],b[2],b[3]) for b in bookings if b[0] in demo_ids]); print("repeat-fault equipment:",[e[0] for e in repeat])
