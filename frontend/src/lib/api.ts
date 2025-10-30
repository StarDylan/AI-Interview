const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export interface ProjectListing {
    id: string;
    name: string;
    creator_name: string;
    created_at: string;
}

/**
 * Helper function to make authenticated API calls
 */
async function authenticatedFetch<T>(
    endpoint: string,
    token: string,
    options?: RequestInit,
): Promise<T> {
    const response = await fetch(`${BACKEND_URL}${endpoint}`, {
        ...options,
        headers: {
            ...options?.headers,
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error(
            `API request failed: ${response.status} ${response.statusText}`,
        );
    }

    return response.json();
}

/**
 * Fetch all projects from the backend
 */
export async function fetchProjects(token: string): Promise<ProjectListing[]> {
    return authenticatedFetch<ProjectListing[]>("/project", token);
}

/**
 * Create a new project
 */
export async function createProject(
    projectName: string,
    token: string,
): Promise<ProjectListing> {
    return authenticatedFetch<ProjectListing>(
        `/project?project_name=${encodeURIComponent(projectName)}`,
        token,
        { method: "POST" },
    );
}
