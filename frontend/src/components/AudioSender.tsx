import { Button, Paper } from "@mantine/core";
import { useToggle } from "@mantine/hooks";
import { IconMicrophone } from "@tabler/icons-react";

export function AudioSender() {
    const [value, toggle] = useToggle(["audio_off", "audio_on"] as const);

    // TODO: Use authenticated websocket (or passed one in) and init a webrtc socket on start audio

    return (
        <Paper>
            <Button
                variant={value === "audio_on" ? "filled" : "outline"}
                color={value === "audio_on" ? "red" : undefined}
                leftSection={<IconMicrophone size={16} />}
                size="md"
                radius="lg"
                onClick={() => toggle()}
            >
                {value === "audio_off" && "Start Audio"}
                {value === "audio_on" && "Stop Audio"}
            </Button>
        </Paper>
    );
}
