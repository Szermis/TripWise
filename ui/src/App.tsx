import {Separator} from "@/components/ui/separator"
import {
    SidebarInset,
    SidebarProvider,
    SidebarTrigger,
} from "@/components/ui/sidebar"

import ChatMessages from "./components/chat-messages"
import ChatInput from "@/components/chat-input.tsx";
import {useState} from "react"
import {AppSidebar} from "@/components/app-sidebar.tsx";

export default function App() {
    const [messages, setMessages] = useState([
        {type: "assistant", content: "Hi, how can I help you today?"},
    ])
    // const [value, setValue] = useState("")
    const [loading, setLoading] = useState(false)

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        const value = e.currentTarget.message.value.trim()
        e.currentTarget.reset()
        if (!value.trim() || loading) return

        const message = value
        setLoading(true)
        setMessages((prev) => [...prev, {type: "user", content: message}])


        try {
            // in React

            const res = await fetch(`${import.meta.env.VITE_API_URL}/chat/message`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({message}),
            })

            if (!res.ok) {
                throw new Error("Request failed")
            }

            const data = await res.json()
            setMessages((prev) => [...prev, {type: "assistant", content: data.result}])
        } catch (err) {
            console.error(err)
            setMessages((prev) => [...prev, {type: "assistant", content: "❌ Failed to send message"}])
        } finally {
            setLoading(false)
        }
    }

    return (
        <SidebarProvider>
            <AppSidebar/>
            <SidebarInset>
                <div className="flex flex-col items-center max-h-screen overflow-hiddens">
                    <header
                        className="flex h-16 w-full shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
                        <div className="flex items-center gap-2 px-4">
                            <SidebarTrigger className="-ml-1"/>
                            <Separator
                                orientation="vertical"
                                className="mr-2 data-[orientation=vertical]:h-4"
                            />
                        </div>
                    </header>
                    <ChatMessages messages={messages} isLoading={loading}/>
                    <div className="w-full">
                        <ChatInput onSubmit={handleSubmit} isLoading={loading}/>
                    </div>
                </div>
            </SidebarInset>
        </SidebarProvider>
    )
}
