#!/bin/bash

#######################################
# Configuration
#######################################
BOILERPLATE_README_TITLE="Simple AI agent to chat with a LLM"
BOILERPLATE_README_DESC="This agent will interact with an existing Ollama instance or other AI providers as a chatbot."
BOILERPLATE_FULL_NAME="Simple AI agent"
BOILERPLATE_PROJECT_DIR=ai-agent
BOILERPLATE_REPO_NAME=ai-agent
BOILERPLATE_CLASS_FILE=simple_agent
BOILERPLATE_CLASS_NAME=SimpleAgent
BOILERPLATE_LOCAL_PORT=9201
BOILERPLATE_ENTRYPOINT_NAME=interact

NEW_README_TITLE="My custom AI agent to chat with a LLM"
NEW_README_DESC="My custom AI agent will interact with an existing Ollama instance or other AI providers as a chatbot."
NEW_FULL_NAME="My custom agent"
NEW_PROJECT_DIR=my-custom-agent
NEW_REPO_NAME=my-custom-agent
NEW_CLASS_FILE=my_custom_agent
NEW_CLASS_NAME=MyCustomAgent
NEW_LOCAL_PORT=9202
NEW_ENTRYPOINT_NAME=chat
#######################################

# Colors
BLK='\033[0;30m'
RED='\033[0;31m'
GRN='\033[0;32m'
BRN='\033[0;33m'
YLW='\033[1;33m'
BLU='\033[0;34m'
PRP='\033[0;35m'
CYN='\033[0;36m'
COL1="${GRN}"
COL2="${YLW}"
DEF=$(tput sgr0)

# Banner
clear
echo "${COL1}"
echo "${COL1}  ┏┓     ┏┓        ┏┓   ┏┓                       ┏┓                  "
echo "${COL1}  ┃┃     ┃┃        ┃┃  ┏┛┗┓                     ┏┛┗┓                 "
echo "${COL1}  ┃┗━┳━━┳┫┃┏━━┳━┳━━┫┃┏━┻┓┏╋━━┓  ┏━━┳━━┳━┓┏━━┳━┳━┻┓┏╋━━┳━┓            "
echo "${COL1}  ┃┏┓┃┏┓┣┫┃┃┃━┫┏┫┏┓┃┃┃┏┓┃┃┃┃━┫  ┃┏┓┃┃━┫┏┓┫┃━┫┏┫┏┓┃┃┃┏┓┃┏┛            "
echo "${COL1}  ┃┗┛┃┗┛┃┃┗┫┃━┫┃┃┗┛┃┗┫┏┓┃┗┫┃━┫  ┃┗┛┃┃━┫┃┃┃┃━┫┃┃┏┓┃┗┫┗┛┃┃             "
echo "${COL1}  ┗━━┻━━┻┻━┻━━┻┛┃┏━┻━┻┛┗┻━┻━━┛  ┗━┓┣━━┻┛┗┻━━┻┛┗┛┗┻━┻━━┻┛             "
echo "${COL1}                ┃┃              ┏━┛┃  alessandro.orru@aleostudio.com "
echo "${COL1}                ┗┛              ┗━━┛                                 "
echo "${COL1}"
echo "${DEF}"

# Check configuration
if [ -z ${BOILERPLATE_FULL_NAME+x} ] | [ -z ${BOILERPLATE_PROJECT_DIR+x} ] | [ -z ${BOILERPLATE_REPO_NAME+x} ] | [ -z ${BOILERPLATE_CLASS_FILE+x} ] | [ -z ${BOILERPLATE_CLASS_NAME+x} ] | [ -z ${BOILERPLATE_LOCAL_PORT+x} ] | [ -z ${BOILERPLATE_ENTRYPOINT_NAME+x} ] | [ -z ${NEW_FULL_NAME+x} ] | [ -z ${NEW_PROJECT_DIR+x} ] | [ -z ${NEW_REPO_NAME+x} ] | [ -z ${NEW_CLASS_FILE+x} ] | [ -z ${NEW_CLASS_NAME+x} ] | [ -z ${NEW_LOCAL_PORT+x} ] | [ -z ${NEW_ENTRYPOINT_NAME+x} ]; then
    echo "${RED}[x]${DEF} Missing variables! Unable to continue!"
    echo ""
    exit 1
fi


# Review configuration
echo "${COL1}[!]${DEF} Current configuration"
echo ""
echo "- Old readme title: ${COL2}${BOILERPLATE_README_TITLE}${DEF}"
echo "- New readme title: ${COL2}${NEW_README_TITLE}${DEF}"
echo ""
echo "- Old readme description: ${COL2}${BOILERPLATE_README_DESC}${DEF}"
echo "- New readme description: ${COL2}${NEW_README_DESC}${DEF}"
echo ""
echo "- Old full name: ${COL2}${BOILERPLATE_FULL_NAME}${DEF}"
echo "- New full name dir: ${COL2}${NEW_FULL_NAME}${DEF}"
echo ""
echo "- Old project name: ${COL2}${BOILERPLATE_PROJECT_DIR}${DEF}"
echo "- New project name: ${COL2}${NEW_PROJECT_DIR}${DEF}"
echo ""
echo "- Old repository name: ${COL2}${BOILERPLATE_REPO_NAME}${DEF}"
echo "- New repository name: ${COL2}${NEW_REPO_NAME}${DEF}"
echo ""
echo "- Old class file: ${COL2}${BOILERPLATE_CLASS_FILE}${DEF}"
echo "- New class file: ${COL2}${NEW_CLASS_FILE}${DEF}"
echo ""
echo "- Old class name: ${COL2}${BOILERPLATE_CLASS_NAME}${DEF}"
echo "- New class name: ${COL2}${NEW_CLASS_NAME}${DEF}"
echo ""
echo "- Old local port: ${COL2}${BOILERPLATE_LOCAL_PORT}${DEF}"
echo "- New local port: ${COL2}${NEW_LOCAL_PORT}${DEF}"
echo ""
echo "- Old entrypoint name: ${COL2}${BOILERPLATE_ENTRYPOINT_NAME}${DEF}"
echo "- New entrypoint name: ${COL2}${NEW_ENTRYPOINT_NAME}${DEF}"
echo ""
read -n1 -p "Do you want to continue? [y/n]: " KEY
echo ""


# Boilerplate builder
if [ "$KEY" = "y" ]; then
    echo ""

    export LC_CTYPE=C
    export LANG=C

    echo "${COL1}[!]${DEF} Creating new project boilerplate. Please wait..."
    cd ..
    PROJECTS_PATH=`pwd`
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR
    cp -r $PROJECTS_PATH/$BOILERPLATE_PROJECT_DIR $PROJECTS_PATH/$NEW_PROJECT_DIR
    cd $PROJECTS_PATH/$NEW_PROJECT_DIR
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR/.git
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR/app/__pycache__
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR/app/agent/__pycache__
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR/app/core/__pycache__
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR/app/model/__pycache__
    rm -rf $PROJECTS_PATH/$NEW_PROJECT_DIR/tests/__pycache__

    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_README_TITLE}/${NEW_README_TITLE}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_README_DESC}/${NEW_README_DESC}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_FULL_NAME}/${NEW_FULL_NAME}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_PROJECT_DIR}/${NEW_PROJECT_DIR}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_REPO_NAME}/${NEW_REPO_NAME}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_CLASS_FILE}/${NEW_CLASS_FILE}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_CLASS_NAME}/${NEW_CLASS_NAME}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_LOCAL_PORT}/${NEW_LOCAL_PORT}/g" {} +
    find . -type f -exec sed -i '' -e "s/${BOILERPLATE_ENTRYPOINT_NAME}/${NEW_ENTRYPOINT_NAME}/g" {} +
    echo "${COL1}[v]${DEF} References inside files updated"

    for file in $(find . -type f -name "*${BOILERPLATE_CLASS_FILE}*"); do mv -i -- "$file" "${file//$BOILERPLATE_CLASS_FILE/$NEW_CLASS_FILE}"; done
    echo "${COL1}[v]${DEF} File names replaced"

    echo "${COL1}[v]${DEF} Done! Your new project is ready to be built with these commands:"
    echo ""
    echo "${COL1}cd ${PROJECTS_PATH}/${NEW_PROJECT_DIR}${DEF}"
    echo "${COL1}sh run.sh${DEF}"
    echo ""
    echo "Or if you want to run as container:"
    echo ""
    echo "${COL1}docker-compose build${DEF}"
    echo "${COL1}docker-compose up -d${DEF}"
    echo ""
    echo "${YLW}[!]${DEF} Do not forget to create on GitLab/GitHub the related repository ${COL2}${NEW_REPO_NAME}${DEF} and push all the files! Enjoy!"
    echo ""

elif [ "$KEY" = "n" ]; then
    echo ""
    echo "${COL1}[!]${DEF} Quitting! Bye bye!"
    echo ""

else
    echo ""
    echo "${RED}[x]${DEF} Wrong choice! Exiting..."
    echo ""
fi
