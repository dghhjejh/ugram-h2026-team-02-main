import { useCallback } from 'react';
import { Camera, RefreshCcw, Video, X } from 'lucide-react';
import { useWebcamCapture } from '../../hooks/useWebcamCapture';

type WebcamCaptureModalProps = {
    open: boolean;
    onClose: () => void;
    onUsePhoto: (file: File) => void;
};

export default function WebcamCaptureModal({ open, onClose, onUsePhoto }: WebcamCaptureModalProps) {
    const {
        videoRef,
        isStartingCamera,
        cameraError,
        capturedFile,
        capturedPreviewUrl,
        startCamera,
        capturePhoto,
        retakePhoto,
    } = useWebcamCapture(open);

    const handleUsePhoto = useCallback(() => {
        if (!capturedFile) {
            return;
        }

        onUsePhoto(capturedFile);
        onClose();
    }, [capturedFile, onClose, onUsePhoto]);

    if (!open) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center px-4">
            <div className="w-full max-w-2xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                    <div>
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Take a photo</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Capture a photo and continue in the normal post flow.</p>
                    </div>
                    <button
                        className="text-gray-500 hover:text-gray-800 dark:text-gray-300 dark:hover:text-white text-lg"
                        onClick={onClose}
                        aria-label="Close camera capture"
                    >
                        <X />
                    </button>
                </div>

                <div className="p-5 space-y-4 overflow-y-auto">
                    <div className="rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-gray-950 min-h-80 flex items-center justify-center">
                        {capturedPreviewUrl ? (
                            <img
                                src={capturedPreviewUrl}
                                alt="Captured webcam preview"
                                className="w-full max-h-[60vh] object-contain"
                            />
                        ) : (
                            <div className="relative w-full">
                                <video
                                    ref={videoRef}
                                    className="w-full max-h-[60vh] object-contain"
                                    autoPlay
                                    muted
                                    playsInline
                                />
                                {isStartingCamera && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/65 text-white gap-2">
                                        <Video size={28} />
                                        <p className="text-sm font-medium">Starting webcam…</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {cameraError ? (
                        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-950 dark:bg-red-950/30 dark:text-red-300">
                            {cameraError}
                        </div>
                    ) : (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                            {capturedPreviewUrl
                                ? 'Retake the photo if needed before sending it to the post editor.'
                                : 'Make sure your subject is centered, then capture a still photo.'}
                        </p>
                    )}
                </div>

                <div className="flex justify-end gap-3 px-5 py-4 border-t border-gray-100 dark:border-gray-800">
                    <button type="button" className="btn btn-secondary" onClick={onClose}>
                        Cancel
                    </button>

                    {capturedPreviewUrl ? (
                        <>
                            <button type="button" className="btn btn-secondary" onClick={() => void retakePhoto()}>
                                <span className="inline-flex items-center gap-2">
                                    <RefreshCcw size={16} />
                                    Retake
                                </span>
                            </button>
                            <button type="button" className="btn btn-primary" onClick={handleUsePhoto}>
                                Use this photo
                            </button>
                        </>
                    ) : (
                        <>
                            {cameraError && (
                                <button type="button" className="btn btn-secondary" onClick={() => void startCamera()}>
                                    Retry camera
                                </button>
                            )}
                            <button
                                type="button"
                                className="btn btn-primary"
                                onClick={() => void capturePhoto()}
                                disabled={isStartingCamera || Boolean(cameraError)}
                            >
                                <span className="inline-flex items-center gap-2">
                                    <Camera size={16} />
                                    Capture photo
                                </span>
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
