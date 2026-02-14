"""
Custom Exceptions for College List AI

Hierarchical exception classes for proper error handling across layers.
"""

from typing import Optional, Dict, Any


class CollegeListAIError(Exception):
    """Base exception for all College List AI errors."""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.original_error = original_error

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class ValidationError(CollegeListAIError):
    """Raised when input validation fails."""
    pass


class DatabaseError(CollegeListAIError):
    """Raised when database operations fail."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        super().__init__(message, details, original_error)


class NotFoundError(DatabaseError):
    """Raised when a requested resource is not found."""
    pass


class DuplicateError(DatabaseError):
    """Raised when attempting to create a duplicate resource."""
    pass


class VectorServiceError(CollegeListAIError):
    """Raised when vector embedding operations fail."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        retry_count: int = 0,
        original_error: Optional[Exception] = None
    ):
        details = {"retry_count": retry_count}
        if model:
            details["model"] = model
        super().__init__(message, details, original_error)


class EmbeddingGenerationError(VectorServiceError):
    """Raised when embedding generation fails."""
    pass


class SimilaritySearchError(VectorServiceError):
    """Raised when vector similarity search fails."""
    pass


class AIServiceError(CollegeListAIError):
    """Raised when AI (Groq/Perplexity) operations fail."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if model:
            details["model"] = model
        if operation:
            details["operation"] = operation
        super().__init__(message, details, original_error)


class RateLimitError(AIServiceError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, details=details, original_error=original_error)


class ConfigurationError(CollegeListAIError):
    """Raised when configuration is missing or invalid."""
    
    def __init__(
        self,
        message: str,
        missing_keys: Optional[list] = None,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if missing_keys:
            details["missing_keys"] = missing_keys
        super().__init__(message, details, original_error)
