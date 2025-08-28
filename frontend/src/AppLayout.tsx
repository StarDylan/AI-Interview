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
} from "@mantine/core";

const user = {
    name: "Jane Spoonfighter",
    image: "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/avatars/avatar-5.png",
};

const navItems = [
    { link: "home", label: "Home" },
    { link: "profile", label: "Profile" },
    { link: "settings", label: "Settings" },
];

export default function AppLayout() {
    const [activeTab, setActiveTab] = useState<string | null>("Home");

    return (
        <AppShell header={{ height: 60 }} padding="md">
            <AppShell.Header px="md">
                <Group h="100%" justify="space-between">
                    <Group>
                        <Text fw={700} size="lg">
                            My Application
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
                        <Text fw={500} size="sm">
                            {user.name}
                        </Text>
                        <Avatar
                            src={user.image}
                            alt={user.name}
                            radius="xl"
                            size="md"
                        />
                    </Group>
                    <Menu width="100%" offset={20}>
                        <Menu.Target>
                            <Burger hiddenFrom="sm" size="sm" />
                        </Menu.Target>
                        <Menu.Dropdown>
                            <Menu.Item>Profile</Menu.Item>
                            <Menu.Item>Settings</Menu.Item>
                            <Menu.Item>Logout</Menu.Item>
                        </Menu.Dropdown>
                    </Menu>
                </Group>
            </AppShell.Header>

            <AppShell.Main>
                <Container fluid>
                    <p>
                        The main content of your application goes here. The
                        header and navbar are now controlled by the AppShell
                        component, and the tabs are responsive.
                    </p>
                </Container>
            </AppShell.Main>
        </AppShell>
    );
}
