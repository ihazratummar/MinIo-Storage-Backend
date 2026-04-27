pipeline {
    agent any

    environment {
        IMAGE = "minio-backend:latest"
        CONTAINER = "minio-backend"
        STATIC_IP = "172.25.0.7"
        PORT = "7000"
        ENV_FILE = "/home/envs/minio-backend.env"
    }

    stages {

        stage('Pull Code') {
            steps {
                script {
                    try {
                        checkout scm
                        echo "✅ Code pulled successfully"
                    } catch (Throwable e) {
                        error "❌ Failed to pull code: ${e}"
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    try {
                        sh "docker build -t ${IMAGE} ."
                        echo "✅ Docker image built successfully"
                    } catch (Throwable e) {
                        error "❌ Failed to build Docker image: ${e}"
                    }
                }
            }
        }

        stage('Stop and Remove Old Container') {
            steps {
                script {
                    try {
                        sh """
                            if docker ps -aq -f name=^${CONTAINER}\$; then
                                docker stop ${CONTAINER} || true
                                docker rm ${CONTAINER} || true
                            fi
                            echo "✅ Old container removed or didn't exist"
                        """
                    } catch (Throwable e) {
                        echo "⚠️ Warning: Cannot remove old container: ${e}"
                    }
                }
            }
        }

        stage('Verify Environment File') {
            steps {
                script {
                    try {
                        sh """
                            if [ ! -f ${ENV_FILE} ]; then
                                echo "❌ Environment file not found at ${ENV_FILE}"
                                exit 1
                            fi
                            echo "✅ Environment file verified"
                        """
                    } catch (Throwable e) {
                        error "❌ ENV check failed: ${e}"
                    }
                }
            }
        }

        stage('Run API Container') {
            steps {
                script {
                    try {
                        sh """
                            docker run -d \
                            --name ${CONTAINER} \
                            --network ${NETWORK} \
                            --ip ${STATIC_IP} \
                            --env-file ${ENV_FILE} \
                            -p ${PORT}:8000 \
                            --restart unless-stopped \
                            ${IMAGE}
                        """
                        echo "✅ API Container started"
                    } catch (Throwable e) {
                        error "❌ Failed to start API container: ${e}"
                    }
                }
            }
        }

        stage('Health Check') {
            steps {
                script {
                    try {
                        sh """
                            sleep 10
                            docker logs --tail 20 ${CONTAINER}
                        """
                        echo "✅ Health check passed"
                    } catch (Throwable e) {
                        error "❌ Health check failed: ${e}"
                    }
                }
            }
        }

        stage('Cleanup Old Images') {
            steps {
                script {
                    try {
                        sh "docker image prune -f || true"
                        echo "✅ Cleanup completed"
                    } catch (Throwable e) {
                        echo "⚠️ Cleanup warning: ${e}"
                    }
                }
            }
        }
    }

    post {
        success {
            echo "🎉 Deployment completed successfully!"
        }
        failure {
            echo "❌ Deployment failed!"
            sh "docker logs ${CONTAINER} || true"
        }
        always {
            echo "Pipeline completed."
        }
    }
}
