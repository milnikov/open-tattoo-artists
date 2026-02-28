export default function ProfilePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Profile</h1>
      <p className="text-gray-600 mb-4">
        Sign in with Google to save favourite artists and tattoos, and track your
        contributions.
      </p>
      <div className="border rounded-lg p-6 bg-white">
        <p className="text-gray-500">
          Supabase auth integration coming soon. Configure{" "}
          <code className="bg-gray-100 px-1 rounded">
            NEXT_PUBLIC_SUPABASE_URL
          </code>{" "}
          and{" "}
          <code className="bg-gray-100 px-1 rounded">
            NEXT_PUBLIC_SUPABASE_ANON_KEY
          </code>{" "}
          in your environment.
        </p>
      </div>
    </div>
  );
}
