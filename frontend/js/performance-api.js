/** Section 8: "No Spring Boot metrics endpoint exists yet. Initially load
 * the supplied experiment fixture." Isolated here so a future real
 * endpoint is a one-file change, not a page rewrite. */
export function createPerformanceApi() {
  return {
    async getResults() {
      await new Promise((resolve) => setTimeout(resolve, 200));
      const response = await fetch("mocks/performance.json");
      return response.json();
    },
  };
}
