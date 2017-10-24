BUCKET := YOUR_BUCKET
REGION := YOUR_REGION

PREFIX := packges
STACK_NAME := "lookout"
PY_VERSION := 3.6

BASE := $(shell /bin/pwd)
PYTHON := $(shell /usr/bin/which python$(PY_VERSION))

invoke:
	sam local invoke $(f) \
	 	--event lambda/$(f)/event.json \
		--env-vars env.json

package:
	sam package \
		--template-file template.yml \
		--s3-bucket $(BUCKET) \
		--s3-prefix $(PREFIX) \
		--output-template-file project.yml \
		--region $(REGION)

deploy:
	sam deploy \
		--template-file project.yml \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_NAMED_IAM \
		--region $(REGION)

outputs:
	@echo stack $(STACK_NAME) output values:

	@aws cloudformation \
		--region $(REGION) \
		describe-stacks --stack-name $(STACK_NAME) \
		--query "Stacks[0].Outputs"

testdata:
	@echo "copying test images to s3 ..."

	@aws s3 sync img/ "s3://`aws cloudformation \
    --region $(REGION) \
    describe-stacks --stack-name $(STACK_NAME) \
    --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" \
    --output text`/img/"

index:
	echo "index faces from s3 bucktet ..."
	@aws lambda invoke \
		--invocation-type RequestResponse \
		--payload '{}' \
		--region $(REGION)  \
		--function-name `aws cloudformation \
			--region $(REGION) \
			describe-stacks --stack-name $(STACK_NAME) \
			--query "Stacks[0].Outputs[?OutputKey=='IndexFaces'].OutputValue" \
			--output text` \
		"/dev/stdout"

release:
	@make package deploy outputs testdata index

deps:
	docker run -v $$PWD:/var/task -it lambci/lambda:build-python3.6 /bin/bash -c 'make do_deps'

do_deps:
	"pip$(PY_VERSION)" \
		install \
		-t "lambda/common/" \
		-r "lambda/common/requirements.txt"

	# for i in $(shell find lambda -mindepth 1 -maxdepth 1 -type d); do \
	# 	cd "$(BASE)/$$i"; \
	# 	if [ -a "$(BASE)/$$i/requirements.txt" ]; then \
	# 		"pip$(PY_VERSION)" \
	# 			install \
	# 			-t "$(BASE)/$$i/" \
	# 			-r "$(BASE)/$$i/requirements.txt"; \
	# 	fi; \
	# done
