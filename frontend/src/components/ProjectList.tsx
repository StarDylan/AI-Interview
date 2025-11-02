import { useState, useEffect } from "react";
import {
    Container,
    Card,
    Text,
    Button,
    Group,
    SimpleGrid,
    Modal,
    TextInput,
    Stack,
    Title,
    Loader,
    Center,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useAuth } from "react-oidc-context";
import { fetchProjects, createProject } from "../lib/api";
import type { ProjectListing } from "../lib/api";

export default function ProjectList() {
    const [projects, setProjects] = useState<ProjectListing[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [createModalOpen, setCreateModalOpen] = useState(false);
    const [newProjectName, setNewProjectName] = useState("");
    const [creating, setCreating] = useState(false);
    const navigate = useNavigate();
    const auth = useAuth();

    useEffect(() => {
        const loadProjects = async () => {
            try {
                setLoading(true);
                setError(null);
                const token = auth.user?.access_token;
                if (!token) {
                    throw new Error("No access token available");
                }
                const data = await fetchProjects(token);
                setProjects(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load projects",
                );
            } finally {
                setLoading(false);
            }
        };

        loadProjects();
    }, []);

    const handleCreateProject = async () => {
        if (!newProjectName.trim()) {
            return;
        }

        try {
            setCreating(true);
            const token = auth.user?.access_token;
            if (!token) {
                throw new Error("No access token available");
            }

            const newProject = await createProject(newProjectName, token);
            setProjects([...projects, newProject]);
            setCreateModalOpen(false);
            setNewProjectName("");
            // Navigate to the new project
            navigate(`/project/${newProject.id}`);
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to create project",
            );
        } finally {
            setCreating(false);
        }
    };

    const handleProjectClick = (projectId: string) => {
        navigate(`/project/${projectId}`);
    };

    if (loading) {
        return (
            <Center style={{ height: "100vh" }}>
                <Loader size="lg" />
            </Center>
        );
    }

    return (
        <Container size="xl" py="xl">
            <Group justify="space-between" mb="xl">
                <Title order={1}>My Projects</Title>
                <Button onClick={() => setCreateModalOpen(true)} size="md">
                    Create Project
                </Button>
            </Group>

            {error && (
                <Text c="red" mb="md">
                    {error}
                </Text>
            )}

            {projects.length === 0 ? (
                <Card shadow="sm" padding="xl" radius="md" withBorder>
                    <Stack align="center" gap="md">
                        <Text size="lg" c="dimmed">
                            No projects yet
                        </Text>
                        <Text size="sm" c="dimmed">
                            Create your first project to get started
                        </Text>
                        <Button onClick={() => setCreateModalOpen(true)}>
                            Create Your First Project
                        </Button>
                    </Stack>
                </Card>
            ) : (
                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
                    {projects.map((project) => (
                        <Card
                            key={project.id}
                            shadow="sm"
                            padding="lg"
                            radius="md"
                            withBorder
                            style={{ cursor: "pointer" }}
                            onClick={() => handleProjectClick(project.id)}
                        >
                            <Stack gap="sm">
                                <Text fw={500} size="lg">
                                    {project.name}
                                </Text>
                                <Text size="xs" c="dimmed">
                                    Created by {project.creator_name}
                                </Text>
                                <Text size="xs" c="dimmed">
                                    {new Date(
                                        project.created_at,
                                    ).toLocaleDateString("en-US", {
                                        year: "numeric",
                                        month: "long",
                                        day: "numeric",
                                    })}
                                </Text>
                            </Stack>
                        </Card>
                    ))}
                </SimpleGrid>
            )}

            <Modal
                opened={createModalOpen}
                onClose={() => {
                    setCreateModalOpen(false);
                    setNewProjectName("");
                }}
                title="Create New Project"
            >
                <Stack>
                    <TextInput
                        label="Project Name"
                        placeholder="Enter project name"
                        value={newProjectName}
                        onChange={(e) =>
                            setNewProjectName(e.currentTarget.value)
                        }
                        onKeyDown={(e) => {
                            if (e.key === "Enter") {
                                handleCreateProject();
                            }
                        }}
                    />
                    <Group justify="flex-end">
                        <Button
                            variant="subtle"
                            onClick={() => {
                                setCreateModalOpen(false);
                                setNewProjectName("");
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleCreateProject}
                            loading={creating}
                            disabled={!newProjectName.trim()}
                        >
                            Create
                        </Button>
                    </Group>
                </Stack>
            </Modal>
        </Container>
    );
}
