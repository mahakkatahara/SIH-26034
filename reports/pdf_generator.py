"""Reports module — Phase 1 stubs for PDF and DOCX generation."""


class PDFGeneratorStub:
    """
    ⚠ PHASE 1 STUB: PDF generation not yet implemented.

    Real implementation will use WeasyPrint + Jinja2 in Phase 8.
    The generated PDF will include:
    - Official report header with government branding
    - Inspection details and metadata
    - Detected declarations with confidence scores
    - Violations and legal references
    - Evidence photographs
    - Inspector remarks and signature block
    """

    def generate(self, inspection_id: str, output_path: str) -> dict:
        """
        Generate a PDF compliance report.

        Args:
            inspection_id: UUID of the inspection.
            output_path: Where to save the PDF file.

        Returns:
            Dict with status and notice.

        Raises:
            NotImplementedError: Always in Phase 1.
        """
        raise NotImplementedError(
            "PDF generation not yet implemented (Phase 8). "
            "This stub confirms the interface. "
            "Real PDF generation using WeasyPrint will be added in Phase 8."
        )


class DOCXGeneratorStub:
    """
    ⚠ PHASE 1 STUB: DOCX generation not yet implemented.

    Real implementation will use python-docx in Phase 8.
    The generated DOCX will be fully editable and contain:
    - Formatted compliance report structure
    - Tables for declarations and violations
    - Embedded evidence images
    - Track changes support for inspector edits
    """

    def generate(self, inspection_id: str, output_path: str) -> dict:
        """
        Generate an editable DOCX compliance report.

        Args:
            inspection_id: UUID of the inspection.
            output_path: Where to save the DOCX file.

        Returns:
            Dict with status and notice.

        Raises:
            NotImplementedError: Always in Phase 1.
        """
        raise NotImplementedError(
            "DOCX generation not yet implemented (Phase 8). "
            "This stub confirms the interface. "
            "Real DOCX generation using python-docx will be added in Phase 8."
        )
