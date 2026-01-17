import {Send} from "lucide-react"
import {InputGroup, InputGroupButton, InputGroupInput} from "@/components/ui/input-group.tsx";

interface Props {
    onSubmit: () => void;
    isLoading?: boolean
}

export default function ChatInput({onSubmit, isLoading}: Props) {
    return (
        <div className="p-4">
            <form onSubmit={onSubmit} className="flex justify-center w-full">
                <InputGroup className="w-2/3">
                    <InputGroupInput
                        name={"message"}
                        placeholder="Type a message…"
                    />
                    <InputGroupButton size="icon-sm" type={"submit"} disabled={isLoading}>
                        <Send/>
                    </InputGroupButton>
                </InputGroup>
            </form>
        </div>
    )
}
