import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';
import { captureVideoFrameAsFile, getWebcamErrorMessage } from '../utils/webcam';

type UseWebcamCaptureResult = {
    videoRef: RefObject<HTMLVideoElement | null>;
    isStartingCamera: boolean;
    cameraError: string | null;
    capturedFile: File | null;
    capturedPreviewUrl: string | null;
    startCamera: () => Promise<void>;
    capturePhoto: () => Promise<void>;
    retakePhoto: () => Promise<void>;
};

export function useWebcamCapture(open: boolean): UseWebcamCaptureResult {
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const openRef = useRef(open);
    const startAttemptRef = useRef(0);
    const [isStartingCamera, setIsStartingCamera] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const [capturedFile, setCapturedFile] = useState<File | null>(null);
    const [capturedPreviewUrl, setCapturedPreviewUrl] = useState<string | null>(null);

    useEffect(() => {
        openRef.current = open;
    }, [open]);

    const stopCamera = useCallback(() => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
    }, []);

    const clearCapturedPreview = useCallback(() => {
        setCapturedPreviewUrl((currentPreviewUrl) => {
            if (currentPreviewUrl) {
                URL.revokeObjectURL(currentPreviewUrl);
            }
            return null;
        });
        setCapturedFile(null);
    }, []);

    const startCamera = useCallback(async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            setCameraError('This browser does not support webcam access.');
            return;
        }

        stopCamera();
        setIsStartingCamera(true);
        setCameraError(null);
        const startAttempt = startAttemptRef.current + 1;
        startAttemptRef.current = startAttempt;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: {
                    facingMode: 'user',
                },
            });

            if (!openRef.current || startAttempt !== startAttemptRef.current) {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }

            streamRef.current = stream;

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play().catch(() => undefined);
            }
        } catch (error) {
            if (openRef.current && startAttempt === startAttemptRef.current) {
                setCameraError(getWebcamErrorMessage(error));
            }
        } finally {
            if (openRef.current && startAttempt === startAttemptRef.current) {
                setIsStartingCamera(false);
            }
        }
    }, [stopCamera]);

    useEffect(() => {
        if (!open) {
            startAttemptRef.current += 1;
            stopCamera();
            clearCapturedPreview();
            setCameraError(null);
            setIsStartingCamera(false);
            return;
        }

        void startCamera();

        return () => {
            startAttemptRef.current += 1;
            stopCamera();
        };
    }, [clearCapturedPreview, open, startCamera, stopCamera]);

    useEffect(() => {
        return () => {
            stopCamera();
            if (capturedPreviewUrl) {
                URL.revokeObjectURL(capturedPreviewUrl);
            }
        };
    }, [capturedPreviewUrl, stopCamera]);

    const capturePhoto = useCallback(async () => {
        const video = videoRef.current;
        if (!video) {
            setCameraError('The webcam is not ready yet. Try again in a moment.');
            return;
        }

        try {
            const file = await captureVideoFrameAsFile(video);
            clearCapturedPreview();
            setCapturedFile(file);
            setCapturedPreviewUrl(URL.createObjectURL(file));
            stopCamera();
        } catch (error) {
            setCameraError(error instanceof Error ? error.message : 'Unable to capture the photo. Please try again.');
        }
    }, [clearCapturedPreview, stopCamera]);

    const retakePhoto = useCallback(async () => {
        clearCapturedPreview();
        setCameraError(null);
        await startCamera();
    }, [clearCapturedPreview, startCamera]);

    return {
        videoRef,
        isStartingCamera,
        cameraError,
        capturedFile,
        capturedPreviewUrl,
        startCamera,
        capturePhoto,
        retakePhoto,
    };
}
