import re
import json
import argparse
import os
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF


class ResumeParser:
    def __init__(self):
        self.extracted_data = {}
        
        # Regex patterns for extraction
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+\d{1,3}[-\.\s]??)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}'
        self.linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9_-]+|LinkedIn'
        self.github_pattern = r'github\.com/[a-zA-Z0-9_-]+|GitHub'
        
        # Common section headers in resumes
        self.section_headers = {
            'education': ['education', 'academic background', 'academic history', 'educational background'],
            'experience': ['experience', 'work experience', 'employment history', 'work history', 'professional experience'],
            'skills': ['skills', 'technical skills', 'core competencies', 'key skills', 'areas of expertise'],
            'projects': ['projects', 'personal projects', 'academic projects', 'key projects'],
            'certifications': ['certifications', 'certificates', 'professional certifications', 'credentials'],
            'languages': ['languages', 'language proficiency', 'spoken languages']
        }

    def parse_resume(self, file_path):
        """Parse resume file (PDF only)"""
        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()
        
        if file_extension != '.pdf':
            print(f"Only PDF format is supported. Provided file: {file_extension}")
            return None
        
        text = self._extract_text_from_pdf(file_path)
        if not text:
            print("Failed to extract text from PDF.")
            return None
        
        # Extract information from the text
        self._extract_information(text)
        return self.extracted_data
    
    def _extract_text_from_pdf(self, file_path):
        """Extract text from PDF file using pdfplumber for better text extraction"""
        text = ""
        try:
            # Use pdfplumber for better formatting preservation
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    if page_text:
                        text += page_text + "\n"
                    
            # If pdfplumber didn't get good results, try PyPDF2 as fallback
            if not text.strip():
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        text += pdf_reader.pages[page_num].extract_text() + "\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
        
        # print(text)
        return text

    
    def extract_hyperlinks_from_pdf(file_path):
        """Extract hyperlinks from PDF file using PyMuPDF to get both link text and URLs"""
        hyperlinks = []
        
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                link_list = page.get_links()
                for link in link_list:
                    if link.get("uri"):
                        # Get the rectangle containing the link
                        rect = link.get("from")
                        
                        # Extract the text in this rectangle if available
                        link_text = ""
                        if rect:
                            words = page.get_text("words", clip=rect)
                            link_text = " ".join([word[4] for word in words]) if words else ""
                        
                        hyperlinks.append({
                            'text': link_text,
                            'url': link.get("uri")
                        })
            doc.close()
        except Exception as e:
            print(f"PyMuPDF extraction error: {str(e)}")
        
        return hyperlinks
        
    def _extract_information(self, text):
        """Extract various information from text"""
        lines = text.split('\n')
        
        # Extract personal information
        personal_info = self._extract_personal_info(text)
        if personal_info:
            self.extracted_data["personal_info"] = personal_info
        
        # First locate all section headings and their line numbers
        section_bounds = self._identify_sections(lines)
        
        # Extract contents of each section
        for section_name, (start_idx, end_idx) in section_bounds.items():
            section_content = '\n'.join(lines[start_idx+1:end_idx]).strip()
            self._process_section(section_name, section_content)
            
        # Check for any sections that might have been missed using heuristics
        self._extract_missing_sections(text)
    
    def _identify_sections(self, lines):
        """Identify sections in the resume and their line bounds"""
        section_bounds = {}
        section_starts = []
        
        # First identify all section headers and their line numbers
        for idx, line in enumerate(lines):
            line_clean = line.strip().lower()
            
            # Skip empty lines
            if not line_clean:
                continue
            
            # Check if this line matches any known section header
            found_section = None
            for section, keywords in self.section_headers.items():
                # Try exact match
                if line_clean in keywords:
                    found_section = section
                    break
                
                # Try partial match - the line contains the keyword
                for keyword in keywords:
                    if keyword in line_clean and len(line_clean) < 30:
                        found_section = section
                        break
                
                if found_section:
                    break
            
            # Special case for sections with unique formatting
            if found_section is None and line_clean == 'work experience':
                found_section = 'experience'
            elif found_section is None and line_clean == 'projects':
                found_section = 'projects'
            
            if found_section:
                section_starts.append((idx, found_section))
        
        # Determine section bounds (start and end lines)
        for i, (start_idx, section_name) in enumerate(section_starts):
            if i < len(section_starts) - 1:
                end_idx = section_starts[i+1][0]
            else:
                end_idx = len(lines)
            
            section_bounds[section_name] = (start_idx, end_idx)
        
        return section_bounds
    
    def _extract_personal_info(self, text):
        """Extract personal information like name, email, phone"""
        personal_info = {}
        
        # Extract email
        emails = re.findall(self.email_pattern, text)
        if emails:
            personal_info["email"] = emails[0]
        
        # Extract phone
        phones = re.findall(self.phone_pattern, text)
        if phones:
            personal_info["phone"] = phones[0]
        
        # Extract LinkedIn
        linkedin = re.findall(self.linkedin_pattern, text)
        if linkedin:
            personal_info["linkedin"] = linkedin[0]
            
        # Extract GitHub
        github = re.findall(self.github_pattern, text)
        if github:
            personal_info["github"] = github[0]
        
        # Try to extract name (this is more challenging)
        # Assuming name might be at the beginning of the resume
        lines = text.split('\n')
        for line in lines[:3]:  # Usually the first line in a resume
            line = line.strip()
            if line and 1 <= len(line.split()) <= 4:  # Most names are 1-4 words
                # Check if this line doesn't contain common headers or contact info
                if not any(word in line.lower() for word in ['resume', 'cv', 'curriculum', 'vitae', 'email', 'phone', '@']):
                    personal_info["name"] = line
                    break
                    
        # Try to extract location/address
        location_pattern = r'Boston, MA|Pune, India'
        location_match = re.search(location_pattern, text)
        if location_match:
            personal_info["location"] = location_match.group(0).strip()
            
        return personal_info
    
    def _process_section(self, section_name, section_text):
        """Process different sections of the resume based on section name"""
        if section_name == "education":
            self.extracted_data["education"] = self._extract_education(section_text)
        elif section_name == "experience":
            self.extracted_data["work_experience"] = self._extract_experience(section_text)
        elif section_name == "skills":
            self.extracted_data["skills"] = self._extract_skills(section_text)
        elif section_name == "projects":
            self.extracted_data["projects"] = self._extract_projects(section_text)
        elif section_name == "certifications":
            self.extracted_data["certifications"] = self._extract_certifications(section_text)
    
    def _extract_missing_sections(self, text):
        """Look for sections that might have been missed in the standard extraction"""
        # Extract certifications if they weren't found in a distinct section
        if "certifications" not in self.extracted_data and "Certification:" in text:
            self.extracted_data["certifications"] = self._extract_certifications(text)
            
        # Look for skills if not already extracted
        if "skills" not in self.extracted_data:
            skill_markers = ["Programming Languages:", "Databases & Tools:", "Cloud Platform"]
            for marker in skill_markers:
                if marker in text:
                    self.extracted_data["skills"] = self._extract_skills(text)
                    break
    
    def _extract_education(self, text):
        """Extract education information"""
        education_entries = []
        
        # Try to split by institution names
        institution_pattern = r'([\w\s]+University|[\w\s]+College|[\w\s]+Institute|University+[\w\s])'
        institutions = re.findall(institution_pattern, text)
        
        # If no clear institutions found, try splitting by paragraphs
        if not institutions:
            entries = text.split('\n\n')
        else:
            # Split by institution names
            entries = []
            current_entry = ""
            lines = text.split('\n')
            current_institution = None
            
            for line in lines:
                inst_match = re.search(institution_pattern, line)
                if inst_match and (not current_institution or current_institution != inst_match.group(1)):
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = line + "\n"
                    current_institution = inst_match.group(1)
                else:
                    current_entry += line + "\n"
            
            if current_entry:
                entries.append(current_entry)
        
        for entry in entries:
            if not entry.strip():
                continue
                
            edu_item = {}
            lines = entry.split('\n')
            
            # Extract institution name
            for i, line in enumerate(lines):
                if "University" in line or "College" in line or "Institute" in line:
                    parts = line.split(',')
                    edu_item["institution"] = parts[0].strip()
                    
                    # Extract location if present
                    if len(parts) > 1:
                        edu_item["location"] = parts[1].strip()
                    break
            
            # Extract degree
            degree_pattern = r'(Master of|Bachelor of|PhD in|Doctorate in|MS in|BS in)[^,\n]+'
            for line in lines:
                degree_match = re.search(degree_pattern, line, re.IGNORECASE)
                if degree_match:
                    edu_item["degree"] = degree_match.group(0).strip()
                    break
                elif "Expected" in line and "202" in line:
                    parts = line.split("Expected")
                    if parts and parts[0].strip():
                        edu_item["degree"] = parts[0].strip()
            
            # Extract graduation date/expected date
            for line in lines:
                expected_match = re.search(r'Expected\s+([\w\s]+\d{4})', line)
                if expected_match:
                    edu_item["expected_graduation"] = expected_match.group(1).strip()
                else:
                    date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\s*-\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}|\d{4}|Present)', line, re.IGNORECASE)
                    if date_match:
                        edu_item["start_date"] = date_match.group(1).strip()
                        edu_item["end_date"] = date_match.group(2).strip()
            
            # Extract GPA
            for line in lines:
                gpa_match = re.search(r'GPA:?\s*(\d+(?:\.\d+)?)', line)
                if gpa_match:
                    edu_item["gpa"] = gpa_match.group(1).strip()
            
            # Extract coursework
            for i, line in enumerate(lines):
                if "Coursework:" in line or "coursework:" in line or "Related Coursework:" in line:
                    course_text = line.split(":", 1)[1].strip()
                    courses = [course.strip() for course in re.split(r',|;', course_text) if course.strip()]
                    if courses:
                        edu_item["coursework"] = courses
            
            if edu_item:
                education_entries.append(edu_item)
        
        return education_entries
    
    def _extract_experience(self, text):
        """Extract work experience information"""
        experience_entries = []
        
        # Split by company entries - try multiple patterns
        entries = []
        
        # First try to split by company | position pattern
        company_pattern = r'([\w\s]+Ltd|[\w\s]+Inc|[\w\s]+Corp|[\w\s]+LLC)\s*\|\s*([^|\n]+)'
        companies = re.findall(company_pattern, text)
        
        if companies:
            # Split text by these companies
            sections = re.split(company_pattern, text)
            
            # Reconstruct experience entries
            current_entry = ""
            for i in range(1, len(sections), 3):  # Skip every 3rd element (matched groups)
                if i+2 < len(sections):
                    company = sections[i].strip()
                    position = sections[i+1].strip()
                    content = sections[i+2]
                    
                    entry = f"{company} | {position}\n{content}"
                    entries.append(entry)
        
        # If no entries found with first pattern, try alternative
        if not entries:
            # Fall back to paragraph splitting
            entries = text.split('\n\n')
            
            # Filter entries that look like job experiences
            entries = [entry for entry in entries if "|" in entry or "•" in entry]
        
        for entry in entries:
            if not entry.strip():
                continue
                
            exp_item = {}
            lines = entry.split('\n')
            
            # Extract company and role (often in format "Company | Role")
            for line in lines:
                if "|" in line:
                    parts = line.split("|", 1)
                    if len(parts) == 2:
                        exp_item["company"] = parts[0].strip()
                        
                        # Position might include date in parentheses
                        position_part = parts[1].strip()
                        if "(" in position_part and ")" in position_part:
                            position, date_part = position_part.split("(", 1)
                            exp_item["position"] = position.strip()
                            
                            # Extract dates
                            date_part = date_part.split(")", 1)[0].strip()
                            if "-" in date_part:
                                start_date, end_date = date_part.split("-", 1)
                                exp_item["start_date"] = start_date.strip()
                                exp_item["end_date"] = end_date.strip()
                        else:
                            exp_item["position"] = position_part
                    break
            
            # If we don't have dates yet, try to find them on the line
            if "start_date" not in exp_item:
                for line in lines:
                    date_match = re.search(r'\(([\w\s]+\d{4})\s*-\s*([\w\s]+\d{4}|Present)\)', line)
                    if date_match:
                        exp_item["start_date"] = date_match.group(1).strip()
                        exp_item["end_date"] = date_match.group(2).strip()
                        break
            
            # Extract location
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                location_match = re.search(r'([\w\s\.-]+,\s*[\w\s\.-]+)', line)
                if location_match:
                    exp_item["location"] = location_match.group(1).strip()
                    break
     

            
            # Extract responsibilities (bullet points)
            responsibilities = []
            for line in lines:
                line = line.strip()
                if line.startswith('•'):
                    clean_line = line.lstrip('• ').strip()
                    if clean_line:
                        responsibilities.append(clean_line)
            
            if responsibilities:
                exp_item["responsibilities"] = responsibilities
            
            if exp_item:
                experience_entries.append(exp_item)
        
        return experience_entries
    
    def _extract_skills(self, text):
        """Extract skills information with categorization"""
        skills_dict = {}
        
        # Look for skill categories common in resumes
        skill_categories = [
            "Programming Languages", "Databases", "Cloud Platform", 
            "Libraries & Frameworks", "Technologies", "Software","Cloud & DevOps"
        ]
        
        lines = text.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a category line
            is_category = False
            for category in skill_categories:
                if line.startswith("• " + category) | line.startswith(category) :
                    current_category = category
                    # print(current_category)
                    skills_text = line.split(":", 1)[1].strip()
                    skills = [skill.strip() for skill in skills_text.split(",") if skill.strip()]
                    skills_dict[current_category] = skills
                    is_category = True
                    break
                    
            # If we have a current category but this isn't a new one, it might be skills for current category
            if not is_category and current_category and ":" not in line and "•" not in line:
                # Looks like additional skills for current category
                if current_category in skills_dict:
                    skills = [skill.strip() for skill in line.split(",") if skill.strip()]
                    skills_dict[current_category].extend(skills)
                    
        # Extract certification from the skills section if present
        for line in lines:
            if "Certification:" in line:
                cert_text = line.split(":", 1)[1].strip()
                if "certifications" not in self.extracted_data:
                    self.extracted_data["certifications"] = [{"name": cert_text}]
                
        return skills_dict
    

    def _extract_projects(self, text):
        """Extract project information without requiring a | character"""
        projects = []
        
        # Try to identify project entries
        lines = text.split('\n')
        project_entries = []
        current_project = None
        current_lines = []
        
        # Common technology keywords that might help identify project headers
        tech_keywords = ["python", "java", "javascript", "react", "node", "aws", "c++", "sql", "docker"]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for project header patterns
            is_project_header = False
            
            # Case 1: Line with | separator
            if "|" in line and len(line.split("|")[0].strip()) < 30:
                is_project_header = True
            
            # Case 2: Line that looks like a title (short, possibly with date or technologies)
            elif (len(line) < 80 and any(keyword.lower() in line.lower() for keyword in tech_keywords)) or \
                (line[0].isupper() and len(line.split()) <= 10 and not line.endswith(":")):
                # This looks like it could be a project title
                is_project_header = True
                
            if is_project_header:
                # Save previous project before starting a new one
                if current_project and current_lines:
                    project_entries.append((current_project, current_lines))
                    
                current_project = line
                current_lines = []
            elif current_project:
                current_lines.append(line)
                
        # Add the last project
        if current_project and current_lines:
            project_entries.append((current_project, current_lines))
            
        # Process each project entry
        for project_header, project_lines in project_entries:
            project = {}
            
            # Parse project name and technologies
            if "|" in project_header:
                parts = project_header.split("|", 1)
                project["name"] = parts[0].strip()
                        
                # Extract technologies
                tech_text = parts[1].strip()
                technologies = [tech.strip() for tech in tech_text.split(",") if tech.strip()]
                if technologies:
                    project["technologies"] = technologies
            else:
                # For projects without | separator, just use the whole line as name
                project["name"] = project_header
                
                # Try to extract technologies from the project name if possible
                potential_techs = []
                for keyword in tech_keywords:
                    if keyword.lower() in project_header.lower():
                        potential_techs.append(keyword)
                
                if potential_techs:
                    project["technologies"] = potential_techs
                    
            # Extract description (bullet points)
            description = []
            for line in project_lines:
                # Handle different bullet point styles
                if any(line.lstrip().startswith(bullet) for bullet in ["•", "-", "–", "*"]):
                    # Remove the bullet and leading space
                    clean_line = line.lstrip()
                    for bullet in ["•", "-", "–", "*"]:
                        if clean_line.startswith(bullet):
                            clean_line = clean_line[len(bullet):].strip()
                            break
                    description.append(clean_line)
                elif line.strip() and not line.endswith(":"):
                    # If it's not a section header, treat as description
                    description.append(line.strip())
                    
            if description:
                project["description"] = description
                
            if project:
                projects.append(project)
                
        return projects
    
    def _extract_certifications(self, text):
        """Extract certifications"""
        certifications = []
        
        # Look for certification mentions
        cert_pattern = r'Certification:?\s*([^•\n,]+)'
        cert_matches = re.findall(cert_pattern, text, re.IGNORECASE)
        
        for cert_text in cert_matches:
            cert_name = cert_text.strip()
            if cert_name:
                certifications.append({"name": cert_name})
                
        return certifications


def main():
    parser = argparse.ArgumentParser(description='Parse resume PDF and convert to JSON')
    parser.add_argument('input_file', help='Path to the resume PDF file')
    parser.add_argument('--output', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Create parser and parse resume
    parser = ResumeParser()
    
    result = parser.parse_resume(args.input_file)
    
    if result:
        # Format output
        output_json = json.dumps(result, indent=2)
        
        # Determine output file path
        if args.output:
            output_file = args.output
        else:
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_file = f"output_parsed.json"
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_json)
        
        print(f"Resume parsed successfully. Output saved to {output_file}")
        # print(output_json)
    else:
        print("Failed to parse resume.")

if __name__ == "__main__":
    main()
    # parser = argparse.ArgumentParser(description='Parse resume PDF and convert to JSON')
    # parser.add_argument('input_file', help='Path to the resume PDF file')
    # parser.add_argument('--output', help='Output JSON file path')
    # args = parser.parse_args()

    
    # sol = ResumeParser()
    # txt = sol._extract_text_from_pdf(args.input_file)
    # response = sol._extract_experience(txt)

    # print(response)    