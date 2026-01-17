import {ScrollArea} from "@/components/ui/scroll-area"
import ChatMessage from "./chat-message"
import { useEffect, useRef } from "react"

interface Message {
    type: "user" | "assistant"
    content: string
}

interface Props {
    messages: Message[]
    isLoading?: boolean
}

export default function ChatMessages({messages, isLoading}: Props) {
    const bottomRef = useRef<HTMLDivElement | null>(null)

    // auto-scroll when messages or loading change
    useEffect(() => {
        bottomRef.current?.scrollIntoView({behavior: "smooth"})
    }, [messages, isLoading])
    return (
        <ScrollArea className="h-full w-2/3 overflow-y-hidden ">
            {messages.map((message) => (
                <ChatMessage content={message.content} isOwn={message.type === 'user'}/>
            ))}
            {isLoading && <ChatMessage content={""} isLoading/>}
            <div ref={bottomRef}/>
        </ScrollArea>
    )
}
