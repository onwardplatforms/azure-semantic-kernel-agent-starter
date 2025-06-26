"use client";

import { useEffect, useState, useRef } from "react";
import { Chat, ChatRef } from "@/components/chat";
import { testApiConnection } from "@/lib/api";
import { AlertCircle, Info } from "lucide-react";
import Link from "next/link";

export default function Home() {
    const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);
    const [apiStatusMessage, setApiStatusMessage] = useState<string>("");
    const chatRef = useRef<ChatRef>(null);

    useEffect(() => {
        const checkApi = async () => {
            const result = await testApiConnection();
            setApiAvailable(result.success);
            setApiStatusMessage(result.message);
        };

        checkApi();
        const interval = setInterval(checkApi, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleReset = () => {
        if (chatRef.current) {
            chatRef.current.reset();
        }
    };

    return (
        <main className="flex h-screen flex-col bg-[#343541]">
            <header className="fixed top-0 left-0 right-0 z-10 h-12 flex items-center border-b border-[#40414f] bg-[#343541]">
                <div className="max-w-3xl mx-auto px-4 w-full flex items-center justify-between">
                    <h1 className="text-lg font-medium text-white">Agent Chat</h1>
                    <div className="flex items-center gap-3">
                        <Link
                            href="/latex-test"
                            className="bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 px-3 py-1 rounded-md flex items-center gap-1 transition-colors"
                        >
                            <span>LaTeX Test</span>
                        </Link>

                        <button
                            onClick={handleReset}
                            className="bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 px-3 py-1 rounded-md flex items-center gap-1 transition-colors"
                        >
                            <Info className="h-3 w-3" />
                            <span>Clear Chat</span>
                        </button>

                        <div className="flex items-center gap-2 text-xs text-gray-400">
                            <div className={`h-2 w-2 rounded-full ${apiAvailable === null ? 'bg-yellow-500' :
                                apiAvailable ? 'bg-green-400' : 'bg-red-500'
                                }`} />
                            <span className="truncate max-w-[180px]">
                                {apiAvailable === null && "Checking API..."}
                                {apiAvailable === true && "Agent Runtime Connected"}
                                {apiAvailable === false && "API unavailable"}
                            </span>
                        </div>
                    </div>
                </div>
            </header>

            <div className="pt-12 h-[calc(100vh-3rem)] flex flex-col">
                {apiAvailable === false && (
                    <div className="py-2 flex items-center justify-center gap-1.5 text-xs text-red-400">
                        <AlertCircle className="h-3.5 w-3.5" />
                        <span>API server is not available: {apiStatusMessage}</span>
                    </div>
                )}
                <div className="flex-1 overflow-hidden">
                    <Chat ref={chatRef} />
                </div>
            </div>
        </main>
    );
}
