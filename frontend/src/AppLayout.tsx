import { useState } from "react";
import {
    AppShell,
    Container,
    Group,
    Text,
    Avatar,
    Burger,
    Button,
    Menu,
    Tooltip,
} from "@mantine/core";
import { User } from "oidc-client-ts";
import { AudioSender } from "./components/AudioSender";
import { Ping } from "./components/Ping";
import StatusDot from "./components/StatusDot";
import { useWebSocket } from "./lib/useWebsocket";

interface AppLayoutProps {
    user?: User | null;
    onSignOut?: () => void;
}

const navItems = [
    { link: "home", label: "Home" },
    { link: "profile", label: "Profile" },
    { link: "settings", label: "Settings" },
];

export default function AppLayout({ user, onSignOut }: AppLayoutProps) {
    const [activeTab, setActiveTab] = useState<string | null>("Home");
    const ws = useWebSocket();

    // Extract user information from OIDC user object
    const userName =
        user?.profile?.name || user?.profile?.preferred_username || "User";
    const userEmail = user?.profile?.email || "";

    // Use first letter of name for avatar if no image
    const avatarText = userName.charAt(0).toUpperCase();

    return (
        <AppShell header={{ height: 60 }} padding="md">
            <AppShell.Header px="md">
                <Group h="100%" justify="space-between">
                    <Group>
                        <Text fw={700} size="lg">
                            Interview Helper
                        </Text>
                    </Group>
                    <Group gap="sm" visibleFrom="sm">
                        {navItems.map((item) => (
                            <Button
                                key={item.link}
                                variant={
                                    activeTab === item.link ? "light" : "subtle"
                                }
                                onClick={() => setActiveTab(item.link)}
                            >
                                {item.label}
                            </Button>
                        ))}
                    </Group>
                    <Group visibleFrom="sm" gap="xs">
                        <Tooltip
                            label="Server Connection Status"
                            arrowOffset={50}
                            arrowSize={8}
                            withArrow
                        >
                            <span>
                                <StatusDot status={ws.connectionStatus} />
                            </span>
                        </Tooltip>
                        <Text fw={500} size="sm">
                            {userName}
                        </Text>
                        <Avatar
                            alt={userName}
                            radius="xl"
                            size="md"
                            color="blue"
                        >
                            {avatarText}
                        </Avatar>
                    </Group>
                    <Menu width="100%" offset={20}>
                        <Menu.Target>
                            <Burger hiddenFrom="sm" size="sm" />
                        </Menu.Target>
                        <Menu.Dropdown>
                            <Menu.Item>Profile</Menu.Item>
                            <Menu.Item>Settings</Menu.Item>
                            <Menu.Item onClick={onSignOut}>Logout</Menu.Item>
                        </Menu.Dropdown>
                    </Menu>
                </Group>
            </AppShell.Header>

            <AppShell.Main>
                <Container fluid>
                    <div style={{ padding: "2rem" }}>
                        <h2>Welcome, {userName}!</h2>
                        {userEmail && <p>Email: {userEmail}</p>}
                        <p>
                            You are successfully authenticated with Google OIDC.
                            The main content of your application goes here.
                        </p>

                        <AudioSender />
                        <Ping />

                        <div style={{ marginTop: "2rem" }}>
                            <Button
                                onClick={onSignOut}
                                variant="outline"
                                color="red"
                            >
                                Sign Out
                            </Button>
                        </div>
                    </div>
                </Container>
            </AppShell.Main>
        </AppShell>
    );
}
