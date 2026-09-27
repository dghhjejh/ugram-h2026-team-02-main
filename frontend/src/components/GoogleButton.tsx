import { useCallback, useState } from 'react';
import { useAuth } from '../context/AuthContext';

type Props = {
    text?: string;
};

export default function GoogleButton({ text = 'Continue with Google' }: Props) {
    const { startGoogleLogin } = useAuth();
    const [working, setWorking] = useState(false);

    const handleClick = useCallback(async () => {
        setWorking(true);
        try {
            startGoogleLogin();
        } finally {
            setWorking(false);
        }
    }, [startGoogleLogin]);

    return (
        <button
            type="button"
            onClick={handleClick}
            disabled={working}
            className="google-btn w-full"
        >
            <img src="/google.svg" alt="Google logo" className="w-5 h-5" />
            <span>{working ? 'Connecting…' : text}</span>
        </button>
    );
}
