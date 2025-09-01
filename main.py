from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field, field_validator
from typing import Annotated, Literal, Optional
import json




app = FastAPI()



class Patient(BaseModel):
    id: Annotated[str, Field(..., description='ID of the patient', example="P001")]
    name: Annotated[str, Field(..., description='Name of the patient', example="John Doe")]
    city: Annotated[str, Field(..., description='City of the patient', example="New York")]
    age: Annotated[int, Field(..., gt=0, lt=110, description='Age of the patient', example=30)] 
    gender: Annotated[Literal['Male', 'Female', 'Others'], Field(..., description='Gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description='Height of the patient in mtrs', example=1.75)] 
    weight: Annotated[float, Field(..., gt=0, description='Weight of the patient in kg', example=70.2)]

    #Normalize gender (so "male" → "Male")
    @field_validator("gender", mode="before")
    def normalize_gender(cls, v):
        if isinstance(v, str):
            return v.capitalize()
        return v

    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height ** 2), 2)
        return bmi
    
    @computed_field
    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return 'Underweight'
        elif 18.5 <= self.bmi < 24.9:
            return 'Normal weight'
        elif 25 <= self.bmi < 29.9:
            return 'Overweight'
        else:
            return 'Obesity'


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    age: Optional[int] = Field(default=None, gt=0)
    gender: Optional[Literal['Male', 'Female', 'Others']] = None   
    height: Optional[float] = Field(default=None, gt=0)
    weight: Optional[float] = Field(default=None, gt=0)

    #Normalize gender here too
    @field_validator("gender", mode="before")
    def normalize_gender(cls, v):
        if isinstance(v, str):
            return v.capitalize()
        return v


def load_data():
    with open("patients.json", "r") as f:
        data = json.load(f)
        return data
  
def save_data(data):
    with open("patients.json", "w") as f:
        json.dump(data, f, indent=2)


@app.get("/")
def hello():
    return {"message": "Patient Management System API"}

@app.get("/about")
def about():
    return {"message": "A full-featured Patient Management System API built to handle patient records"}   

@app.get("/view")
def view():
    data = load_data()
    return data

@app.get("/patient/{patient_id}")
def view_patient(patient_id: str = Path(..., description='ID of the patient in the DB', example='P001')):
    data = load_data()
    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get('/sort')
def sort_patients(sort_by: str = Query(..., description='Sort on the basis of height, weight or bmi'),
                  order: str = Query('asc', description='sort in asc or desc order')):

    valid_fields = ['height', 'weight', 'bmi']
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f'Invalid field select from {valid_fields}')
    
    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail='Invalid order select between asc and desc')
    
    data = load_data()

    #Convert to Patient objects so bmi & verdict are available
    patients = []
    for pid, pdata in data.items():
        pdata["id"] = pid
        patients.append(Patient(**pdata))

    reverse_sort = True if order == 'desc' else False
    sorted_data = sorted([p.model_dump(exclude=["id"]) for p in patients],
                         key=lambda x: x.get(sort_by, 0),
                         reverse=reverse_sort)

    return sorted_data

@app.post("/create")
def create_patient(patient: Patient):
    data = load_data()
    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient ID already exists")

    data[patient.id] = patient.model_dump(exclude=['id'])
    save_data(data)
    return JSONResponse(status_code=201, content={"message": "Patient record created successfully"})

@app.put("/edit/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_patient_data = data[patient_id]
    updated_patient_data = patient_update.model_dump(exclude_unset=True)

    for key, value in updated_patient_data.items():
        existing_patient_data[key] = value

    #Recompute BMI & verdict
    existing_patient_data['id'] = patient_id
    patient_pydantic_obj = Patient(**existing_patient_data)
    existing_patient_data = patient_pydantic_obj.model_dump(exclude=['id'])
  
    data[patient_id] = existing_patient_data
    save_data(data)
    return JSONResponse(status_code=200, content={"message": "Patient record updated successfully"})

@app.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
  data = load_data()

  if patient_id not in data:
      raise HTTPException(status_code=404, detail="Patient not found")  
  
  del data[patient_id]
  save_data(data)
  return JSONResponse(status_code=200, content={"message": "Patient record deleted successfully"})
