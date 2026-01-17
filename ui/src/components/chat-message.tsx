import {Avatar, AvatarFallback} from "@/components/ui/avatar"
import {cn} from "@/lib/utils"
import {Bot} from "lucide-react";
import {Skeleton} from "./ui/skeleton";

type MessageProps = {
    content: string
    isOwn?: boolean
    isLoading?: boolean
}

export default function ChatMessage({content, isOwn, isLoading}: MessageProps) {
    return (
        <div
            className={cn(
                "flex gap-3 px-4 py-2",
                isOwn && "justify-end"
            )}
        >

            {isLoading ? (
                <div className="flex items-center space-x-4">
                    <Avatar>
                        <Skeleton className="h-12 w-12 rounded-full"/>
                    </Avatar>
                    <Skeleton className="rounded-2xl px-4 py-2 text-sm"/>
                </div>
            ) : (
                <>
                    {
                        !isOwn && (
                            <Avatar>
                                <AvatarFallback><Bot/></AvatarFallback>
                            </Avatar>
                        )
                    }

                    <div
                        className={cn(
                            "max-w-[90%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap",
                            isOwn
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted"
                        )}
                    >
                        {content}
                    </div>
                </>
            )}
        </div>
    )
}
