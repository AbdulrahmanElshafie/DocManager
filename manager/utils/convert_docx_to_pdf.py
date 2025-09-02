"""
DOCX to PDF conversion utility module
"""
import os
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


class DocxToPdfConverter:
    """Utility class for converting DOCX files to PDF format"""
    
    @staticmethod
    def convert_docx_to_pdf(input_path_or_buffer: Union[str, Path, bytes]) -> bytes:
        """
        Convert DOCX file to PDF format
        
        Args:
            input_path_or_buffer: Path to DOCX file or bytes buffer
            
        Returns:
            bytes: PDF file content as bytes
            
        Raises:
            ValueError: If input file is not valid DOCX
            RuntimeError: If conversion fails
        """
        temp_files_to_cleanup = []
        
        try:
            # Handle different input types
            if isinstance(input_path_or_buffer, bytes):
                # Create temporary input file from bytes
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_input:
                    temp_input.write(input_path_or_buffer)
                    input_path = temp_input.name
                    temp_files_to_cleanup.append(input_path)
            else:
                input_path = str(input_path_or_buffer)
                
            # Validate input file exists and is DOCX
            if not os.path.exists(input_path):
                raise ValueError(f"Input file does not exist: {input_path}")
                
            if not input_path.lower().endswith('.docx'):
                raise ValueError(f"Input file is not a DOCX file: {input_path}")
            
            # Try LibreOffice conversion first
            try:
                return DocxToPdfConverter._convert_with_libreoffice(input_path)
            except Exception as e:
                logger.warning(f"LibreOffice library conversion failed: {e}")
                # Try system soffice as fallback
                try:
                    return DocxToPdfConverter._convert_with_soffice(input_path)
                except Exception as e2:
                    logger.warning(f"System LibreOffice conversion failed: {e2}")
                    # Final fallback: extract text and create basic PDF
                    return DocxToPdfConverter._convert_with_basic_pdf(input_path)
                
        except Exception as e:
            logger.error(f"DOCX to PDF conversion failed: {e}")
            raise RuntimeError(f"Failed to convert DOCX to PDF: {str(e)}") from e
        finally:
            # Clean up temporary files
            for temp_file in temp_files_to_cleanup:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary file {temp_file}: {e}")
    
    @staticmethod
    def _convert_with_libreoffice(input_path: str) -> bytes:
        """Convert using libreoffice-convert library"""
        try:
            # Try different import methods for libreoffice conversion
            try:
                from libreoffice_convert.converter import PythonLibreOffice
                
                # Use the python libreoffice API
                converter = PythonLibreOffice()
                
                # Create output file path
                output_path = input_path.replace('.docx', '.pdf')
                
                # Convert the file
                success = converter.convertFile('pdf', input_path)
                converter.terminateProcess()
                
                if success and os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        pdf_data = f.read()
                    # Clean up output file
                    os.unlink(output_path)
                    return pdf_data
                else:
                    raise RuntimeError("Conversion failed or output not found")
                    
            except ImportError:
                # Try alternative import
                import docx2pdf
                
                # Create output file path
                output_path = input_path.replace('.docx', '.pdf')
                
                # Convert using docx2pdf
                docx2pdf.convert(input_path, output_path)
                
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        pdf_data = f.read()
                    # Clean up output file
                    os.unlink(output_path)
                    return pdf_data
                else:
                    raise RuntimeError("docx2pdf conversion failed")
                    
        except ImportError:
            raise RuntimeError("No suitable LibreOffice conversion library available")
        except Exception as e:
            raise RuntimeError(f"LibreOffice conversion failed: {e}") from e
    
    @staticmethod
    def _convert_with_soffice(input_path: str) -> bytes:
        """Convert using system soffice binary as fallback"""
        try:
            # Create temporary output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run soffice conversion
                cmd = [
                    'soffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', temp_dir,
                    input_path
                ]
                
                logger.info(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    raise RuntimeError(f"soffice conversion failed: {result.stderr}")
                
                # Find the generated PDF
                input_basename = os.path.splitext(os.path.basename(input_path))[0]
                pdf_path = os.path.join(temp_dir, f"{input_basename}.pdf")
                
                if not os.path.exists(pdf_path):
                    # Try to find any PDF file in the output directory
                    pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
                    if pdf_files:
                        pdf_path = os.path.join(temp_dir, pdf_files[0])
                    else:
                        raise RuntimeError(f"Expected PDF output not found: {pdf_path}")
                
                # Read PDF content
                with open(pdf_path, 'rb') as pdf_file:
                    return pdf_file.read()
                    
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice conversion timed out")
        except FileNotFoundError:
            raise RuntimeError("LibreOffice (soffice) not found. Please install LibreOffice.")
        except Exception as e:
            raise RuntimeError(f"System soffice conversion failed: {e}") from e

    @staticmethod
    def _convert_with_basic_pdf(input_path: str) -> bytes:
        """
        Fallback converter that extracts text from DOCX and creates a basic PDF
        This is used for development/testing when LibreOffice is not available
        """
        try:
            from fpdf import FPDF
            from docx import Document
            
            # Read the DOCX file
            doc = Document(input_path)
            
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            
            # Add title
            filename = os.path.basename(input_path)
            pdf.cell(0, 10, f'Converted from: {filename}', 0, 1, 'C')
            pdf.ln(10)
            
            # Add content
            pdf.set_font('Arial', '', 12)
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    # Handle text encoding
                    try:
                        # Simple text wrapping for long lines
                        if len(text) > 80:
                            words = text.split()
                            current_line = ""
                            for word in words:
                                if len(current_line + word) < 80:
                                    current_line += word + " "
                                else:
                                    if current_line:
                                        pdf.cell(0, 6, current_line.strip().encode('latin1', 'replace').decode('latin1'), 0, 1)
                                    current_line = word + " "
                            if current_line:
                                pdf.cell(0, 6, current_line.strip().encode('latin1', 'replace').decode('latin1'), 0, 1)
                        else:
                            pdf.cell(0, 6, text.encode('latin1', 'replace').decode('latin1'), 0, 1)
                    except Exception as text_error:
                        # Fallback for text encoding issues
                        pdf.cell(0, 6, f"[Content with encoding issues]", 0, 1)
                        logger.warning(f"Text encoding issue: {text_error}")
                    pdf.ln(2)
            
            # Add footer
            pdf.ln(10)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 10, 'This PDF was generated from a DOCX file. Formatting may be simplified.', 0, 1, 'C')
            
            # Return PDF as bytes
            return bytes(pdf.output())
            
        except Exception as e:
            logger.error(f"Basic PDF conversion failed: {e}")
            raise RuntimeError(f"Failed to create basic PDF: {e}") from e


def convert_docx_to_pdf(input_path_or_buffer: Union[str, Path, bytes]) -> bytes:
    """
    Convenience function to convert DOCX to PDF
    
    Args:
        input_path_or_buffer: Path to DOCX file or bytes buffer
        
    Returns:
        bytes: PDF file content as bytes
    """
    return DocxToPdfConverter.convert_docx_to_pdf(input_path_or_buffer)