# import os
# import re
# import json
# import argparse
# from datetime import datetime
# import PyPDF2
# from bs4 import BeautifulSoup
# import pdfplumber

# class ResumeParser:
#     def __init__(self):
#         self.extracted_data = {
#             "personal_info": {},
#             "education": [],
#             "experience": [],
#             "skills": [],
#             "languages": [],
#             "certifications": []
#         }
        
#         # Regex patterns for extraction
#         self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
#         self.phone_pattern = r'(\+\d{1,3}[-\.\s]??)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}'
#         self.linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9_-]+'
#         self.github_pattern = r'github\.com/[a-zA-Z0-9_-]+'
#         self.education_keywords = ['education', 'university', 'college', 'school', 'degree', 'bachelor', 'master', 'phd', 'diploma']
#         self.experience_keywords = ['experience', 'work', 'employment', 'job', 'career', 'position','intern']
#         self.skills_keywords = ['skills', 'technologies', 'tools', 'frameworks', 'languages', 'proficient in']

#     def parse_resume(self, file_path):
#         """Parse resume file based on its extension"""
#         _, file_extension = os.path.splitext(file_path)
#         file_extension = file_extension.lower()
        
#         text = ""
#         if file_extension == '.pdf':
#             text = self._extract_text_from_pdf(file_path)
        
#         # Extract information from the text
#         self._extract_information(text)
#         return self.extracted_data
    
#     def _extract_text_from_pdf(self, file_path):
#         """Extract text from PDF file using PyPDF2 and pdfplumber for better text extraction"""
#         text = ""
#         try:
#             # Try pdfplumber first, which often gives better results with formatting
#             with pdfplumber.open(file_path) as pdf:
#                 for page in pdf.pages:
#                     text += page.extract_text() + "\n"
                    
#             # If pdfplumber didn't get good results, try PyPDF2 as fallback
#             if not text.strip():
#                 with open(file_path, 'rb') as file:
#                     pdf_reader = PyPDF2.PdfReader(file)
#                     for page_num in range(len(pdf_reader.pages)):
#                         text += pdf_reader.pages[page_num].extract_text() + "\n"
#         except Exception as e:
#             print(f"Error extracting text from PDF: {str(e)}")
        
#         return text
    
    
#     def _extract_information(self, text):
#         """Extract various information from text"""
#         lines = text.split('\n')
        
#         # Extract personal information
#         self._extract_personal_info(text)
        
#         # Extract sections
#         current_section = None
#         section_text = ""
        
#         for line in lines:
#             line = line.strip()
#             if not line:
#                 continue
                
#             # Check if this line is a section header
#             line_lower = line.lower()
            
#             if any(keyword in line_lower for keyword in self.education_keywords) and len(line) < 30:
#                 if current_section:
#                     self._process_section(current_section, section_text)
#                 current_section = "education"
#                 section_text = ""
#             elif any(keyword in line_lower for keyword in self.experience_keywords) and len(line) < 30:
#                 if current_section:
#                     self._process_section(current_section, section_text)
#                 current_section = "experience"
#                 section_text = ""
#             elif any(keyword in line_lower for keyword in self.skills_keywords) and len(line) < 30:
#                 if current_section:
#                     self._process_section(current_section, section_text)
#                 current_section = "skills"
#                 section_text = ""
#             elif "certification" in line_lower and len(line) < 30:
#                 if current_section:
#                     self._process_section(current_section, section_text)
#                 current_section = "certifications"
#                 section_text = ""
#             elif "language" in line_lower and "programming" not in line_lower and len(line) < 30:
#                 if current_section:
#                     self._process_section(current_section, section_text)
#                 current_section = "languages"
#                 section_text = ""
#             else:
#                 if current_section:
#                     section_text += line + "\n"
        
#         # Process the last section
#         if current_section:
#             self._process_section(current_section, section_text)
            
#         # If skills are not detected by section headers, try to extract them differently
#         if not self.extracted_data["skills"]:
#             self._extract_skills(text)
    
#     def _extract_personal_info(self, text):
#         """Extract personal information like name, email, phone"""
#         # Extract email
#         emails = re.findall(self.email_pattern, text)
#         if emails:
#             self.extracted_data["personal_info"]["email"] = emails[0]
        
#         # Extract phone
#         phones = re.findall(self.phone_pattern, text)
#         if phones:
#             self.extracted_data["personal_info"]["phone"] = phones[0]
        
#         # Extract LinkedIn
#         linkedin = re.findall(self.linkedin_pattern, text)
#         if linkedin:
#             self.extracted_data["personal_info"]["linkedin"] = linkedin[0]
            
#         # Extract GitHub
#         github = re.findall(self.github_pattern, text)
#         if github:
#             self.extracted_data["personal_info"]["github"] = github[0]
        
#         # Try to extract name (this is more challenging)
#         # Assuming name might be at the beginning of the resume
#         lines = text.split('\n')
#         for line in lines[:5]:  # Check first 5 lines
#             line = line.strip()
#             if line and 2 <= len(line.split()) <= 4:  # Most names are 2-4 words
#                 # Check if this line doesn't contain common headers or contact info
#                 if not any(word in line.lower() for word in ['resume', 'cv', 'curriculum', 'vitae', 'email', 'phone', '@']):
#                     self.extracted_data["personal_info"]["name"] = line
#                     break
    
#     def _process_section(self, section_name, section_text):
#         """Process different sections of the resume"""
#         if section_name == "education":
#             self._extract_education(section_text)
#         elif section_name == "experience":
#             self._extract_experience(section_text)
#         elif section_name == "skills":
#             self._extract_skills(section_text)
#         elif section_name == "certifications":
#             self._extract_certifications(section_text)
#         elif section_name == "languages":
#             self._extract_languages(section_text)
    
#     def _extract_education(self, text):
#         """Extract education information"""
#         # Split into possible education entries
#         education_entries = re.split(r'\n\s*\n', text)
        
#         for entry in education_entries:
#             if not entry.strip():
#                 continue
                
#             edu_item = {}
            
#             # Try to extract degree
#             degree_patterns = [
#                 r'(bachelor|master|phd|doctorate|associate|b\.s\.|m\.s\.|b\.a\.|m\.a\.|b\.eng|m\.eng|b\.tech|m\.tech|b\.b\.a\.|m\.b\.a\.)',
#                 r'(Bachelor|Master|PhD|Doctorate|Associate|B\.S\.|M\.S\.|B\.A\.|M\.A\.|B\.Eng|M\.Eng|B\.Tech|M\.Tech|B\.B\.A\.|M\.B\.A\.)'
#             ]
            
#             for pattern in degree_patterns:
#                 degree_match = re.search(pattern, entry, re.IGNORECASE)
#                 if degree_match:
#                     edu_item["degree"] = entry[max(0, degree_match.start()-10):degree_match.end()+30].strip()
#                     break
            
#             # Try to extract institution
#             institution_words = ['university', 'college', 'school', 'institute', 'academy']
#             for word in institution_words:
#                 if word in entry.lower():
#                     # Get the line containing the institution
#                     lines = entry.split('\n')
#                     for line in lines:
#                         if word in line.lower():
#                             edu_item["institution"] = line.strip()
#                             break
#                     break
            
#             # Try to extract dates
#             date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|(?:19|20)\d{2})'
#             dates = re.findall(date_pattern, entry)
#             if len(dates) >= 2:
#                 edu_item["start_date"] = dates[0]
#                 edu_item["end_date"] = dates[1]
#             elif len(dates) == 1:
#                 edu_item["end_date"] = dates[0]
                
#             # Extract GPA if available
#             gpa_pattern = r'(GPA|gpa)[:;]?\s*(\d+\.\d+)'
#             gpa_match = re.search(gpa_pattern, entry)
#             if gpa_match:
#                 edu_item["gpa"] = gpa_match.group(2)
            
#             # Add to education list if we found something
#             if edu_item:
#                 self.extracted_data["education"].append(edu_item)
    
#     def _extract_experience(self, text):
#         """Extract work experience information"""
#         # Split into possible experience entries
#         experience_entries = re.split(r'\n\s*\n', text)
        
#         for entry in experience_entries:
#             if not entry.strip():
#                 continue
                
#             exp_item = {}
#             lines = entry.split('\n')
            
#             # Try to extract company and position
#             if lines:
#                 exp_item["position"] = lines[0].strip()
#                 if len(lines) > 1:
#                     exp_item["company"] = lines[1].strip()
            
#             # Try to extract dates
#             date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|(?:19|20)\d{2})'
#             dates = re.findall(date_pattern, entry)
#             if len(dates) >= 2:
#                 exp_item["start_date"] = dates[0]
#                 exp_item["end_date"] = dates[1]
#             elif len(dates) == 1:
#                 exp_item["end_date"] = dates[0]
                
#             # Extract description
#             description_lines = []
#             capture_desc = False
#             for i, line in enumerate(lines):
#                 if i > 1:  # Skip title and company lines
#                     # Skip date lines
#                     if re.search(date_pattern, line):
#                         continue
                    
#                     # Add to description
#                     clean_line = line.strip()
#                     if clean_line:
#                         description_lines.append(clean_line)
            
#             if description_lines:
#                 exp_item["description"] = " ".join(description_lines)
            
#             # Add to experience list if we found something
#             if exp_item:
#                 self.extracted_data["experience"].append(exp_item)
    
#     def _extract_skills(self, text):
#         """Extract skills information"""
#         # Simple approach: Split by commas and other separators
#         skills_text = text.lower()
        
#         # Remove common headers
#         for header in ['skills:', 'technical skills:', 'technologies:', 'competencies:']:
#             skills_text = skills_text.replace(header, '')
        
#         # Try to split by various separators
#         skill_separators = [',', '•', '|', '\n', ';']
#         skills_list = []
        
#         for separator in skill_separators:
#             if separator in skills_text:
#                 skills_list = [skill.strip() for skill in skills_text.split(separator) if skill.strip()]
#                 break
        
#         # If still no skills found, try to extract words that might be skills
#         if not skills_list:
#             # List of common programming languages and technologies
#             common_tech = ['python', 'java', 'javascript', 'html', 'css', 'sql', 'c++', 'c#', 'ruby', 
#                            'php', 'swift', 'typescript', 'react', 'angular', 'vue', 'node', 'django', 
#                            'flask', 'spring', 'express', 'mongodb', 'mysql', 'postgresql', 'aws', 'azure', 
#                            'docker', 'kubernetes', 'git', 'jira', 'agile', 'scrum', 'rest', 'graphql']
            
#             # Extract words that match common technologies
#             for tech in common_tech:
#                 if tech in skills_text:
#                     skills_list.append(tech)
        
#         # Add to skills list
#         self.extracted_data["skills"] = list(set(skills_list))  # Remove duplicates
    
#     def _extract_certifications(self, text):
#         """Extract certifications"""
#         lines = text.split('\n')
#         for line in lines:
#             line = line.strip()
#             if line:
#                 # Check if the line appears to be a certification
#                 if ('certified' in line.lower() or 'certification' in line.lower() or 
#                     'certificate' in line.lower() or 'license' in line.lower()):
#                     self.extracted_data["certifications"].append({"name": line})
  
# def main():
#     parser = argparse.ArgumentParser(description='Parse resume and convert to JSON')
#     parser.add_argument('input_file', help='tanmy.pdf')
#     parser.add_argument('--output', help='Output JSON file path')
    
#     args = parser.parse_args()
    
#     # Create parser and parse resume
#     parser = ResumeParser()
#     result = parser.parse_resume(args.input_file)
    
#     if result:
#         # Format output
#         output_json = json.dumps(result, indent=2)
        
#         # Determine output file path
#         if args.output:
#             output_file = args.output
#         else:
#             base_name = os.path.splitext(os.path.basename(args.input_file))[0]
#             output_file = f"{base_name}_parsed.json"
        
#         # Write to file
#         with open(output_file, 'w', encoding='utf-8') as f:
#             f.write(output_json)
        
#         print(f"Resume parsed successfully. Output saved to {output_file}")
#         print(output_json)
#     else:
#         print("Failed to parse resume.")

# if __name__ == "__main__":
#     main()



import os
import re
import json
import argparse
# from datetime import datetime
import PyPDF2
# from bs4 import BeautifulSoup
import pdfplumber

class ResumeParser:
    def __init__(self):
        self.extracted_data = {}  # Empty dictionary to store all sections
        
        # Regex patterns for extraction
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+\d{1,3}[-\.\s]??)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}'
        self.linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9_-]+'
        self.github_pattern = r'github\.com/[a-zA-Z0-9_-]+'
        self.education_keywords = ['education', 'university', 'college', 'school', 'degree', 'bachelor', 'master', 'phd', 'diploma']
        self.experience_keywords = ['experience', 'work', 'employment', 'job', 'career', 'position']
        self.skills_keywords = ['skills', 'technologies', 'tools', 'frameworks', 'languages', 'proficient in']

    def parse_resume(self, file_path):
        """Parse resume file based on its extension"""
        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()
        
        text = ""
        if file_extension == '.pdf':
            text = self._extract_text_from_pdf(file_path)
        
        # Extract information from the text
        self._extract_information(text)
        return self.extracted_data
    
    def _extract_text_from_pdf(self, file_path):
        """Extract text from PDF file using PyPDF2 and pdfplumber for better text extraction"""
        text = ""
        try:
            # Try pdfplumber first, which often gives better results with formatting
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                    
            # If pdfplumber didn't get good results, try PyPDF2 as fallback
            if not text.strip():
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        text += pdf_reader.pages[page_num].extract_text() + "\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
        
        return text
    
    
    def _extract_information(self, text):
        """Extract various information from text"""
        lines = text.split('\n')
        
        # Extract personal information first
        personal_info = self._extract_personal_info(text)
        if personal_info:
            self.extracted_data["personal_info"] = personal_info
        
        # Extract sections based on headers in the text
        sections = {}
        current_section = None
        current_heading = None
        section_text = ""
        
        # First pass: identify all section headings
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Is this a potential heading? Check if it's short and formatted differently
            if len(line) < 40 and (line.isupper() or line.endswith(':') or 
                                   (i > 0 and i < len(lines)-1 and not lines[i-1].strip() and not lines[i+1].strip())):
                
                # Clean up the heading name
                heading = line.strip(':').strip()
                heading_key = heading.lower().strip()
                
                # Replace spaces with underscores and remove special characters for JSON keys
                heading_key = re.sub(r'[^a-z0-9_]', '', heading_key.replace(' ', '_'))
                
                if heading_key:
                    sections[heading_key] = {'text': '', 'original_heading': heading}
                    
        # Second pass: extract text for each section
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line matches any of our identified section headings
            is_heading = False
            for section_key, section_info in sections.items():
                if line == section_info['original_heading']:
                    current_section = section_key
                    is_heading = True
                    break
                    
            if not is_heading and current_section:
                sections[current_section]['text'] += line + "\n"
        
        # Process each section appropriately
        for section_key, section_info in sections.items():
            section_text = section_info['text']
            
            # Process based on section type
            if any(keyword in section_key for keyword in ['education', 'academic', 'degree']):
                self.extracted_data[section_key] = self._extract_education(section_text)
            elif any(keyword in section_key for keyword in ['experience', 'employment', 'work', 'job']):
                self.extracted_data[section_key] = self._extract_experience(section_text)
            elif any(keyword in section_key for keyword in ['skill', 'technical', 'technology']):
                self.extracted_data[section_key] = self._extract_skills(section_text)
            elif any(keyword in section_key for keyword in ['certification', 'certificate']):
                self.extracted_data[section_key] = self._extract_certifications(section_text)
            elif any(keyword in section_key for keyword in ['language', 'languages']):
                self.extracted_data[section_key] = self._extract_languages(section_text)
            else:
                # For unrecognized sections, just keep the text as is
                self.extracted_data[section_key] = section_text.strip()
        
        # Process the last section
        if current_section:
            self._process_section(current_section, section_text)
            
        # If skills are not detected by section headers, try to extract them differently
        if not self.extracted_data["skills"]:
            self._extract_skills(text)
    
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
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and 2 <= len(line.split()) <= 4:  # Most names are 2-4 words
                # Check if this line doesn't contain common headers or contact info
                if not any(word in line.lower() for word in ['resume', 'cv', 'curriculum', 'vitae', 'email', 'phone', '@']):
                    personal_info["name"] = line
                    break
                    
        # Also try to extract address (common in resumes)
        address_pattern = r'\b\d+\s+[A-Za-z0-9\s,\.]+\b(?:Avenue|Lane|Road|Boulevard|Drive|Street|Ave|Dr|Rd|Blvd|Ln|St)\.?'
        address_match = re.search(address_pattern, text)
        if address_match:
            personal_info["address"] = address_match.group(0)
            
        return personal_info
    
    def _process_section(self, section_name, section_text):
        """Process different sections of the resume - this is now handled differently
        and this method is kept for backward compatibility"""
        pass
    
    def _extract_education(self, text):
        """Extract education information"""
        # Split into possible education entries
        education_entries = re.split(r'\n\s*\n', text)
        
        edu_items = []
        for entry in education_entries:
            if not entry.strip():
                continue
                
            edu_item = {}
            
            # Try to extract degree
            degree_patterns = [
                r'(bachelor|master|phd|doctorate|associate|b\.s\.|m\.s\.|b\.a\.|m\.a\.|b\.eng|m\.eng|b\.tech|m\.tech|b\.b\.a\.|m\.b\.a\.)',
                r'(Bachelor|Master|PhD|Doctorate|Associate|B\.S\.|M\.S\.|B\.A\.|M\.A\.|B\.Eng|M\.Eng|B\.Tech|M\.Tech|B\.B\.A\.|M\.B\.A\.)'
            ]
            
            for pattern in degree_patterns:
                degree_match = re.search(pattern, entry, re.IGNORECASE)
                if degree_match:
                    edu_item["degree"] = entry[max(0, degree_match.start()-10):degree_match.end()+30].strip()
                    break
            
            # Try to extract institution
            institution_words = ['university', 'college', 'school', 'institute', 'academy']
            for word in institution_words:
                if word in entry.lower():
                    # Get the line containing the institution
                    lines = entry.split('\n')
                    for line in lines:
                        if word in line.lower():
                            edu_item["institution"] = line.strip()
                            break
                    break
            
            # Try to extract dates
            date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|(?:19|20)\d{2})'
            dates = re.findall(date_pattern, entry)
            if len(dates) >= 2:
                edu_item["start_date"] = dates[0]
                edu_item["end_date"] = dates[1]
            elif len(dates) == 1:
                edu_item["end_date"] = dates[0]
                
            # Extract GPA if available
            gpa_pattern = r'(GPA|gpa)[:;]?\s*(\d+\.\d+)'
            gpa_match = re.search(gpa_pattern, entry)
            if gpa_match:
                edu_item["gpa"] = gpa_match.group(2)
            
            # Extract courses if mentioned
            if "courses" in entry.lower() or "coursework" in entry.lower():
                course_section = re.search(r'(courses|coursework)[:\s]+(.*?)(?:\n\n|\Z)', entry.lower(), re.DOTALL | re.IGNORECASE)
                if course_section:
                    course_text = course_section.group(2)
                    courses = [c.strip() for c in re.split(r'[,;]|\n', course_text) if c.strip()]
                    if courses:
                        edu_item["courses"] = courses
            
            # Add to education list if we found something
            if edu_item:
                edu_items.append(edu_item)
                
        return edu_items
    
    def _extract_experience(self, text):
        """Extract work experience information"""
        # Split into possible experience entries
        experience_entries = re.split(r'\n\s*\n', text)
        
        exp_items = []
        for entry in experience_entries:
            if not entry.strip():
                continue
                
            exp_item = {}
            lines = entry.split('\n')
            
            # Try to extract company and position
            if lines:
                exp_item["position"] = lines[0].strip()
                if len(lines) > 1:
                    exp_item["company"] = lines[1].strip()
            
            # Try to extract dates
            date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|(?:19|20)\d{2})'
            dates = re.findall(date_pattern, entry)
            if len(dates) >= 2:
                exp_item["start_date"] = dates[0]
                exp_item["end_date"] = dates[1]
            elif len(dates) == 1:
                exp_item["end_date"] = dates[0]
            
            # Try to extract location
            location_pattern = r'(?:located in|location[:;]|based in)\s+([A-Za-z\s,\.]+)'
            location_match = re.search(location_pattern, entry, re.IGNORECASE)
            if location_match:
                exp_item["location"] = location_match.group(1).strip()
            else:
                # Try to identify city, state format
                city_state_pattern = r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s+([A-Z]{2})\b'
                city_state_match = re.search(city_state_pattern, entry)
                if city_state_match:
                    exp_item["location"] = city_state_match.group(0)
                
            # Extract description
            description_lines = []
            bullet_points = []
            for i, line in enumerate(lines):
                if i > 1:  # Skip title and company lines
                    # Skip date lines
                    if re.search(date_pattern, line):
                        continue
                    
                    # Check if this is a bullet point
                    clean_line = line.strip()
                    if clean_line.startswith('•') or clean_line.startswith('-') or clean_line.startswith('*'):
                        bullet_points.append(clean_line.lstrip('•-* '))
                    elif clean_line:
                        description_lines.append(clean_line)
            
            if description_lines:
                exp_item["description"] = " ".join(description_lines)
            
            if bullet_points:
                exp_item["achievements"] = bullet_points
            
            # Add to experience list if we found something
            if exp_item:
                exp_items.append(exp_item)
                
        return exp_items
    
    def _extract_skills(self, text):
        """Extract skills information"""
        # Simple approach: Split by commas and other separators
        skills_text = text.lower()
        
        # Remove common headers
        for header in ['skills:', 'technical skills:', 'technologies:', 'competencies:']:
            skills_text = skills_text.replace(header, '')
        
        # Try to split by various separators
        skill_separators = [',', '•', '|', '\n', ';']
        skills_list = []
        
        for separator in skill_separators:
            if separator in skills_text:
                skills_list = [skill.strip() for skill in skills_text.split(separator) if skill.strip()]
                if skills_list:
                    break
        
        # If still no skills found, try to extract words that might be skills
        if not skills_list:
            # List of common programming languages and technologies
            common_tech = ['python', 'java', 'javascript', 'html', 'css', 'sql', 'c++', 'c#', 'ruby', 
                           'php', 'swift', 'typescript', 'react', 'angular', 'vue', 'node', 'django', 
                           'flask', 'spring', 'express', 'mongodb', 'mysql', 'postgresql', 'aws', 'azure', 
                           'docker', 'kubernetes', 'git', 'jira', 'agile', 'scrum', 'rest', 'graphql']
            
            # Extract words that match common technologies
            for tech in common_tech:
                if tech in skills_text:
                    skills_list.append(tech)
        
        # Try to group skills by categories if they appear to be grouped
        skill_groups = {}
        lines = text.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this looks like a category header
            if line.endswith(':') and len(line) < 30 and not line.startswith('•') and not line.startswith('-'):
                current_category = line.rstrip(':').strip()
                skill_groups[current_category] = []
            elif current_category and (line.startswith('•') or line.startswith('-') or ',' in line):
                # This is a skills line under a category
                category_skills = [s.strip() for s in re.split(r'[,•\-|;]', line) if s.strip()]
                skill_groups[current_category].extend(category_skills)
        
        # Return either categorized skills or a flat list
        if skill_groups and len(skill_groups) > 1:
            # Return categorized skills
            return skill_groups
        else:
            # Return list of deduplicated skills
            return list(set(skills_list))
    
    def _extract_certifications(self, text):
        """Extract certifications"""
        cert_items = []
        
        # Split into possible certification entries
        cert_entries = re.split(r'\n\s*\n', text)
        for entry in cert_entries:
            lines = entry.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    # Check if the line appears to be a certification
                    if ('certified' in line.lower() or 'certification' in line.lower() or 
                        'certificate' in line.lower() or 'license' in line.lower()):
                        cert_item = {"name": line}
                        
                        # Try to extract date
                        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|(?:19|20)\d{2})'
                        date_match = re.search(date_pattern, line)
                        if date_match:
                            cert_item["date"] = date_match.group(0)
                            
                        # Try to extract issuer
                        issuer_pattern = r'(?:issued by|from|by)\s+([A-Za-z\s\.]+)'
                        issuer_match = re.search(issuer_pattern, line, re.IGNORECASE)
                        if issuer_match:
                            cert_item["issuer"] = issuer_match.group(1).strip()
                            
                        cert_items.append(cert_item)
        
        return cert_items
    
    def _extract_languages(self, text):
        """Extract languages"""
        language_items = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Common languages
                common_languages = ['english', 'spanish', 'french', 'german', 'chinese', 'japanese', 
                                   'russian', 'arabic', 'hindi', 'portuguese', 'italian', 'korean',
                                   'vietnamese', 'thai', 'dutch', 'swedish']

def main():
    parser = argparse.ArgumentParser(description='Parse resume and convert to JSON')
    parser.add_argument('input_file', help='Path to the resume file')
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
            output_file = f"{base_name}_parsed.json"
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_json)
        
        print(f"Resume parsed successfully. Output saved to {output_file}")
        print(output_json)
    else:
        print("Failed to parse resume.")

if __name__ == "__main__":
    main()