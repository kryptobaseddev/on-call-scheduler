#!/bin/bash

# Helper function for colored output
function print_color {
    local color_code=$1
    local message=$2
    echo -e "\033[${color_code}m${message}\033[0m"
}

# Function to check if a branch exists
function branch_exists {
    local branch=$1
    git show-ref --verify --quiet refs/heads/$branch
}

# Step 1: Define commit message type, scope, and description
print_color "34" "Step 1: Commit Message Creation"
echo "Please select the commit type:"
select type in "feat" "fix" "docs" "style" "refactor" "test" "chore"; do
    if [ -n "$type" ]; then
        break
    fi
done

read -p "Enter the commit scope (e.g., login, database, etc.): " scope
read -p "Enter a short commit description: " description

commit_message="$type($scope): $description"
print_color "32" "Commit Message: $commit_message"

# Step 2: Stage changes
print_color "34" "Step 2: Staging Changes"
echo "Do you want to stage specific files or all changes?"
select choice in "Specific Files" "All Changes"; do
    case $choice in
        "Specific Files")
            git status
            read -p "Enter the file paths to stage (space-separated): " files
            git add $files
            break
            ;;
        "All Changes")
            git add .
            break
            ;;
    esac
done

# Step 3: Check staged files status
print_color "34" "Step 3: Checking Staged Files"
git status

# Step 4: Confirm and commit the changes
read -p "Do you want to commit the staged changes with the message '$commit_message'? (y/n): " confirm_commit
if [ "$confirm_commit" == "y" ]; then
    git commit -m "$commit_message"
else
    print_color "31" "Commit aborted. Please modify your changes and try again."
    exit 1
fi

# Step 5: Check if origin exists
print_color "34" "Step 5: Checking Git Remote Origin"
if git config remote.origin.url > /dev/null; then
    print_color "32" "Origin found. Proceeding with pull and push steps."
else
    print_color "33" "No remote origin found. Do you want to add a remote origin now? (y/n)"
    read add_origin
    if [ "$add_origin" == "y" ]; then
        read -p "Enter the remote repository URL: " remote_url
        git remote add origin $remote_url
        print_color "32" "Remote origin added. Proceeding with pull and push steps."
    else
        print_color "31" "No remote origin set. Proceeding with local-only changes."
        # Continue with local changes only
        exit 0
    fi
fi

# Step 6: Determine branch to pull from
print_color "34" "Step 6: Determining Branch to Pull From"
current_branch=$(git branch --show-current)
if branch_exists "main"; then
    branch_to_pull="main"
elif branch_exists "develop"; then
    print_color "33" "Main branch does not exist. Using 'develop' branch as default."
    branch_to_pull="develop"
else
    print_color "31" "No main or develop branch found. Please create a branch to proceed."
    exit 1
fi

# Step 7: Pull latest changes from origin
if [ "$current_branch" != "$branch_to_pull" ]; then
    print_color "34" "Step 7: Pulling Latest Changes from Origin $branch_to_pull"
    git fetch origin $branch_to_pull
    git checkout $branch_to_pull
    git pull origin $branch_to_pull
    if [ $? -ne 0 ]; then
        print_color "31" "Error pulling from origin. Please resolve conflicts if any."
        exit 1
    fi
    git checkout $current_branch
    git merge $branch_to_pull
else
    print_color "34" "Step 7: Pulling Latest Changes from Origin $branch_to_pull"
    git pull origin $branch_to_pull
    if [ $? -ne 0 ]; then
        print_color "31" "Error pulling from origin. Please resolve conflicts if any."
        exit 1
    fi
fi

# Step 8: Push branch to origin
print_color "34" "Step 8: Pushing Branch to Origin"
git push origin $current_branch

# Step 9: Assess if a Pull Request (PR) is needed
print_color "34" "Step 9: Assessing Pull Request Requirement"
read -p "Do you need to create a Pull Request for this branch? (y/n): " pr_needed
if [ "$pr_needed" == "y" ]; then
    print_color "33" "Please create a Pull Request via your Git hosting service (e.g., GitHub, GitLab)."
fi

# Step 10: Review commits for release and squash if needed
print_color "34" "Step 10: Reviewing Commits for Release"
read -p "Do you need to squash commits before merging? (y/n): " squash_needed
if [ "$squash_needed" == "y" ]; then
    git rebase -i HEAD~n  # Replace n with the number of commits to review
fi

# Step 11: Merge the PR with a clean history
print_color "34" "Step 11: Merging Pull Request"
echo "Select merge option:"
select merge_option in "Squash and Merge" "Rebase and Merge"; do
    case $merge_option in
        "Squash and Merge")
            print_color "33" "Proceed with Squash and Merge via your Git hosting service."
            break
            ;;
        "Rebase and Merge")
            print_color "33" "Proceed with Rebase and Merge via your Git hosting service."
            break
            ;;
    esac
done

# Step 12: Determine if tagging for release is needed
print_color "34" "Step 12: Tagging for Release"
read -p "Is this a release-ready version? (y/n): " release_ready
if [ "$release_ready" == "y" ]; then
    # Step 12.1: Manage versioning
    if [ ! -f version.txt ]; then
        echo "0.1.0" > version.txt
    fi

    current_version=$(cat version.txt)
    IFS='.' read -r -a version_parts <<< "$current_version"
    major=${version_parts[0]}
    minor=${version_parts[1]}
    patch=${version_parts[2]}

    echo "Select version increment type:"
    select version_type in "MAJOR" "MINOR" "PATCH"; do
        case $version_type in
            "MAJOR")
                major=$((major + 1))
                minor=0
                patch=0
                break
                ;;
            "MINOR")
                minor=$((minor + 1))
                patch=0
                break
                ;;
            "PATCH")
                patch=$((patch + 1))
                break
                ;;
        esac
    done

    new_version="$major.$minor.$patch"
    echo $new_version > version.txt

    read -p "Enter the new release version (e.g., v$new_version): " version
git tag -a $version -m "Release $version: $description"
    git push origin $version
fi

# Step 13: Update or create the CHANGELOG.md
print_color "34" "Step 13: Updating CHANGELOG.md"
if [ ! -f CHANGELOG.md ]; then
    print_color "33" "CHANGELOG.md not found. Creating one."
    echo "# Changelog" > CHANGELOG.md
fi
echo -e "\n## $version - $(date +%Y-%m-%d)\n- $commit_message" >> CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs(changelog): update changelog for $version"
git push origin $current_branch

print_color "32" "Process Complete!"
