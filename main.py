from fastapi import FastAPI, Header, BackgroundTasks, HTTPException
from pydantic import BaseModel
from pptx import Presentation
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64, uuid, tempfile, os

app = FastAPI()
jobs = {}
class PPTReq(BaseModel):
    pmids: list[str] | None = None
    email: str

@app.post("/generatePptAndSend")
async def generate(req: PPTReq,
                   authorization: str = Header(...),
                   bt: BackgroundTasks = BackgroundTasks()):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued"}
    bt.add_task(worker, job_id, req.pmids or [], req.email, authorization)
    return {"jobId": job_id, "message": "started"}

def worker(job_id, pmids, email, auth):
    jobs[job_id]["status"] = "running"
    prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "自動生成 PPT"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as f:
        prs.save(f.name); file_path = f.name
    sg = SendGridAPIClient(api_key=auth.split()[-1])
    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    attachment = Attachment(FileContent(data), FileName("paper.pptx"),
                            FileType("application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                            Disposition("attachment"))
    msg = Mail(from_email=os.getenv("FROM_EMAIL", "no-reply@example.com"),
               to_emails=email, subject="自動生成論文スライド",
               plain_text_content="PPT を添付しました。")
    msg.attachment = attachment
    sg.send(msg)
    jobs[job_id] = {"status": "finished"}

@app.get("/jobs/{job_id}")
def job(job_id: str):
    return jobs.get(job_id) or HTTPException(404, "not found")
