// The user as our own backend knows them (not the Clerk user object)
export interface AuthUser {
  id: string;
  email: string;
}
