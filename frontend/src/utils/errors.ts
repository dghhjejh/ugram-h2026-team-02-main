/**
 * Utility functions for error handling
 */

/**
 * Safely extract error message from various error types
 * Prevents "[object Object]" display issues
 */
export const extractErrorMessage = (err: unknown): string => {
    if (err instanceof Error) {
        return err.message;
    }
    if (typeof err === 'string') {
        return err;
    }
    if (err && typeof err === 'object') {
        // Try to find a message property
        if ('message' in err && typeof err.message === 'string') {
            return err.message;
        }
        // Try to find a detail property (common in API errors)
        if ('detail' in err && typeof err.detail === 'string') {
            return err.detail;
        }
        // Try to find an error property
        if ('error' in err && typeof err.error === 'string') {
            return err.error;
        }
        // Handle Pydantic validation errors
        if ('detail' in err && Array.isArray(err.detail)) {
            const validationErrors = err.detail
                .map((validationError) => {
                    if (validationError && typeof validationError === 'object' && 'msg' in validationError) {
                        const location = 'loc' in validationError && Array.isArray(validationError.loc)
                            ? String(validationError.loc.join('.'))
                            : undefined;
                        const message = typeof validationError.msg === 'string' ? validationError.msg : 'Validation error';
                        return location ? `${location}: ${message}` : message;
                    }
                    if (typeof validationError === 'string') {
                        return validationError;
                    }
                    return 'Validation error';
                })
                .join(', ');
            return validationErrors || 'Validation failed';
        }
        // Try to find an errors array (validation errors)
        if ('errors' in err && Array.isArray(err.errors) && err.errors.length > 0) {
            const firstError = err.errors[0];
            if (typeof firstError === 'string') {
                return firstError;
            }
            if (firstError && typeof firstError === 'object' && 'message' in firstError) {
                return String(firstError.message);
            }
        }
    }
    return 'An unexpected error occurred';
};

/**
 * Format error message with context for better user experience
 */
export const formatErrorMessage = (err: unknown, context?: string): string => {
    const message = extractErrorMessage(err);
    return context ? `${context}: ${message}` : message;
};
