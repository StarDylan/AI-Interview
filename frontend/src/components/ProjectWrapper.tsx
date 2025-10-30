import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "react-oidc-context";
import { Center, Loader, Text } from "@mantine/core";
import { fetchProjects } from "../lib/api";
import type { ProjectListing } from "../lib/api";
import AppLayout from "../AppLayout";
import type { User } from "oidc-client-ts";

interface ProjectWrapperProps {
    user?: User | null;
    onSignOut?: () => void;
}

export default function ProjectWrapper({
    user,
    onSignOut,
}: ProjectWrapperProps) {
    const { projectId } = useParams<{ projectId: string }>();
    const [projects, setProjects] = useState<ProjectListing[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const auth = useAuth();

    useEffect(() => {
        const loadProjects = async () => {
            try {
                setLoading(true);
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
    }, [auth.user?.access_token]);

    if (loading) {
        return (
            <Center style={{ height: "100vh" }}>
                <Loader size="lg" />
            </Center>
        );
    }

    if (error) {
        return (
            <Center style={{ height: "100vh" }}>
                <Text c="red">{error}</Text>
            </Center>
        );
    }

    const currentProject = projects.find((p) => p.id === projectId);

    if (!currentProject) {
        return (
            <Center style={{ height: "100vh" }}>
                <Text c="red">Project not found</Text>
            </Center>
        );
    }

    return (
        <AppLayout user={user} onSignOut={onSignOut} project={currentProject} />
    );
}
