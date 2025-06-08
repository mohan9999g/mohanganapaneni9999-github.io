from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import xml.etree.ElementTree as ET
from typing import Dict, List
import re

app = FastAPI(title="EDI Converter API", 
              description="API for converting EDI files to JSON and XML formats")

# Helper function to parse EDI segments
def parse_edi_segments(edi_content: str) -> Dict[str, List[List[str]]]:
    """
    Parses raw EDI content into a structured dictionary
    Format: {segment_type: [list_of_elements]}
    """
    edi_data = {}
    segments = edi_content.strip().split("~")
    
    for segment in segments:
        if not segment:
            continue
        parts = segment.split("*")
        segment_type = parts[0]
        elements = parts[1:]
        
        if segment_type not in edi_data:
            edi_data[segment_type] = []
        edi_data[segment_type].append(elements)
    
    return edi_data

# Helper function to convert EDI to XML
def edi_to_xml(edi_data: Dict[str, List[List[str]]]) -> str:
    """Converts parsed EDI data to XML format"""
    root = ET.Element("EDI_Document")
    
    for segment_type, segment_list in edi_data.items():
        segment_parent = ET.SubElement(root, segment_type)
        
        for i, elements in enumerate(segment_list, 1):
            segment = ET.SubElement(segment_parent, f"{segment_type}_{i}")
            
            for j, element in enumerate(elements, 1):
                ET.SubElement(segment, f"Element_{j}").text = element
    
    return ET.tostring(root, encoding="unicode")

@app.get("/", response_class=PlainTextResponse)
def read_root():
    """Health check endpoint"""
    return "EDI Converter API is running. Use POST /convert with an EDI file to convert."

@app.post("/convert", 
          summary="Convert EDI to JSON/XML",
          response_description="The converted EDI data")
async def convert_edi_file(
    file: UploadFile = File(..., description="EDI file to convert"),
    output_format: str = "json"
):
    """
    Converts an EDI file to specified format (JSON or XML)
    
    - **file**: EDI file to process
    - **output_format**: Desired output format (json/xml)
    """
    try:
        # Read and decode EDI file
        contents = await file.read()
        edi_content = contents.decode("utf-8").strip()
        
        # Validate basic EDI structure
        if not edi_content or "~" not in edi_content or "*" not in edi_content:
            raise HTTPException(status_code=400, detail="Invalid EDI file format")
        
        # Parse EDI segments
        parsed_data = parse_edi_segments(edi_content)
        
        # Return in requested format
        if output_format.lower() == "xml":
            xml_data = edi_to_xml(parsed_data)
            return PlainTextResponse(content=xml_data, media_type="application/xml")
        else:
            return JSONResponse(content={
                "message": "EDI successfully converted",
                "filename": file.filename,
                "data": parsed_data
            })
            
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))